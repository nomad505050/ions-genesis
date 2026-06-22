import uuid
import json
import random
import httpx
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from app.core.database import get_db
from app.core.config import settings
from app.models.artifacts import Relationship, CBB
from app.models.schemas import RelationshipCreate, RelationshipResponse
from app.services.hashing import canonical_hash

router = APIRouter(prefix="/relationship", tags=["relationships"])

# Simple in-memory job tracking
generation_jobs: dict = {}

RELATIONSHIP_TYPES = [
    "supports", "contradicts", "depends_on", "causes",
    "correlates_with", "extends", "refines", "references"
]

GENERATION_PROMPT = """You are a knowledge graph builder for IONS Genesis.

Given source CBBs and target CBBs, find genuine relationships between them.

Rules:
1. Only suggest relationships with confidence >= 0.60
2. Relationship types: supports, contradicts, depends_on, causes, correlates_with, extends, refines, references
3. Aim for 3-5 relationships per source CBB where genuine connections exist
4. Cross-domain connections are valuable — look for them
5. Return ONLY valid JSON, no markdown, no explanation

Output schema:
{
  "relationships": [
    {
      "source_cbb_id": "cbb_xxx",
      "target_cbb_id": "cbb_yyy",
      "relationship_type": "supports",
      "confidence": 0.8,
      "rationale": "one sentence explaining the connection"
    }
  ]
}"""


async def generate_relationships_batch(
    source_batch: list,
    seed_cbbs: list,
    existing: set,
    db: AsyncSession
) -> int:
    """Call OpenRouter to find relationships between source and seed CBBs."""
    sources_text = "\n".join([
        f"SOURCE {c['cbb_id']}: {c['content'][:150]}"
        for c in source_batch
    ])
    seeds_text = "\n".join([
        f"TARGET {c['cbb_id']}: {c['content'][:150]}"
        for c in seed_cbbs
    ])

    user_prompt = f"""SOURCE CBBs (find relationships FROM these):
{sources_text}

TARGET CBBs (find relationships TO these):
{seeds_text}

Find all meaningful relationships. Cross-domain connections are valuable.
Confidence >= 0.60. Aim for 3-5 per source CBB."""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.default_model,
                    "messages": [
                        {"role": "system", "content": GENERATION_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 3000,
                    "temperature": 0.2,
                }
            )
            data = resp.json()
            if "choices" not in data:
                return 0

            raw = data["choices"][0]["message"]["content"].strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            first = raw.index("{")
            last = raw.rindex("}") + 1
            json_str = raw[first:last]

            try:
                suggestions = json.loads(json_str).get("relationships", [])
            except json.JSONDecodeError:
                # Salvage individual relationship objects
                import re
                suggestions = []
                for m in re.findall(r'\{[^{}]*"source_cbb_id"[^{}]*\}', json_str, re.DOTALL):
                    try:
                        obj = json.loads(m)
                        if "source_cbb_id" in obj and "target_cbb_id" in obj:
                            suggestions.append(obj)
                    except Exception:
                        continue

    except Exception:
        return 0

    batch_ids = {c["cbb_id"] for c in source_batch}
    all_ids = {c["cbb_id"] for c in source_batch} | {c["cbb_id"] for c in seed_cbbs}
    created = 0

    for s in suggestions:
        src = s.get("source_cbb_id", "")
        tgt = s.get("target_cbb_id", "")
        rel = s.get("relationship_type", "references")
        conf = float(s.get("confidence", 0.75))
        rat = s.get("rationale", "")

        if rel not in RELATIONSHIP_TYPES:
            continue
        if (src, tgt) in existing:
            continue
        if conf < 0.60:
            continue
        if src not in all_ids or tgt not in all_ids:
            continue
        if src not in batch_ids:
            continue

        rel_id = f"rel_{uuid.uuid4().hex[:12]}"
        payload = {
            "source_cbb_id": src,
            "target_cbb_id": tgt,
            "relationship_type": rel,
            "confidence": conf,
            "rationale": rat,
            "status": "published",
        }
        h = canonical_hash({**payload, "relationship_id": rel_id})
        relationship = Relationship(
            relationship_id=rel_id,
            creator=settings.node_id,
            hash=h,
            **payload
        )
        db.add(relationship)
        existing.add((src, tgt))
        created += 1

    if created > 0:
        await db.commit()

    return created


@router.post("/generate")
async def start_generation(
    background_tasks: BackgroundTasks,
    limit: int = 100,
    min_existing: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Start server-side relationship generation as a background task.
    Returns immediately with a job_id to poll for status.
    """
    if not settings.openrouter_api_key:
        raise HTTPException(
            status_code=400,
            detail="OPENROUTER_API_KEY not configured on this node"
        )

    job_id = uuid.uuid4().hex[:8]
    generation_jobs[job_id] = {
        "status": "running",
        "created": 0,
        "processed": 0,
        "total": 0,
        "message": "Starting...",
    }

    background_tasks.add_task(run_generation, job_id, limit, min_existing)

    return {"job_id": job_id, "status": "running"}


@router.get("/generate/{job_id}")
async def get_generation_status(job_id: str):
    """Poll for relationship generation job status."""
    job = generation_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


async def run_generation(job_id: str, limit: int, min_existing: int):
    """Background task that runs the actual generation."""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # Fetch all published CBBs
            result = await db.execute(select(CBB).where(CBB.status == "published"))
            all_cbbs = [
                {"cbb_id": c.cbb_id, "content": c.content, "domain": c.domain}
                for c in result.scalars().all()
            ]

            if not all_cbbs:
                generation_jobs[job_id] = {"status": "done", "created": 0, "processed": 0, "total": 0, "message": "No published CBBs found"}
                return

            # Count existing relationships
            rel_result = await db.execute(
                select(Relationship.source_cbb_id, func.count())
                .where(Relationship.status == "published")
                .group_by(Relationship.source_cbb_id)
            )
            connection_counts = {row[0]: row[1] for row in rel_result.fetchall()}

            underconnected = [
                c for c in all_cbbs
                if connection_counts.get(c["cbb_id"], 0) < min_existing
            ]

            if not underconnected:
                generation_jobs[job_id] = {
                    "status": "done", "created": 0, "processed": 0,
                    "total": len(all_cbbs),
                    "message": f"All CBBs have {min_existing}+ relationships"
                }
                return

            random.shuffle(underconnected)
            to_process = underconnected[:limit]

            existing_result = await db.execute(
                select(Relationship.source_cbb_id, Relationship.target_cbb_id)
                .where(Relationship.status == "published")
            )
            existing = set(existing_result.fetchall())

            generation_jobs[job_id]["total"] = len(to_process)
            total_created = 0
            batch_size = 5
            seed_size = 15

            for i in range(0, len(to_process), batch_size):
                batch = to_process[i:i + batch_size]
                batch_ids = {c["cbb_id"] for c in batch}
                candidates = [c for c in all_cbbs if c["cbb_id"] not in batch_ids]
                seeds = random.sample(candidates, min(seed_size, len(candidates)))

                created = await generate_relationships_batch(batch, seeds, existing, db)
                total_created += created

                generation_jobs[job_id].update({
                    "processed": i + len(batch),
                    "created": total_created,
                    "message": f"Processing batch {i//batch_size + 1}...",
                })

            generation_jobs[job_id] = {
                "status": "done",
                "created": total_created,
                "processed": len(to_process),
                "total": len(to_process),
                "message": f"Done — {total_created} relationships created",
            }

        except Exception as e:
            generation_jobs[job_id] = {
                "status": "error",
                "created": 0,
                "processed": 0,
                "total": 0,
                "message": str(e),
            }


@router.post("", response_model=RelationshipResponse)
async def create_relationship(payload: RelationshipCreate, db: AsyncSession = Depends(get_db)):
    for cbb_id in [payload.source_cbb_id, payload.target_cbb_id]:
        result = await db.execute(select(CBB).where(CBB.cbb_id == cbb_id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"CBB {cbb_id} not found")
    rel_id = f"rel_{uuid.uuid4().hex[:12]}"
    data = payload.model_dump()
    h = canonical_hash({**data, "relationship_id": rel_id})
    rel = Relationship(
        relationship_id=rel_id,
        creator="genesis_node",
        hash=h,
        **data
    )
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    return rel


@router.get("/{relationship_id}", response_model=RelationshipResponse)
async def get_relationship(relationship_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Relationship).where(Relationship.relationship_id == relationship_id)
    )
    rel = result.scalar_one_or_none()
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return rel


@router.get("", response_model=list[RelationshipResponse])
async def list_relationships(
    source_cbb_id: Optional[str] = None,
    target_cbb_id: Optional[str] = None,
    relationship_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    query = select(Relationship).where(Relationship.status == "published")
    if source_cbb_id:
        query = query.where(Relationship.source_cbb_id == source_cbb_id)
    if target_cbb_id:
        query = query.where(Relationship.target_cbb_id == target_cbb_id)
    if relationship_type:
        query = query.where(Relationship.relationship_type == relationship_type)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()

