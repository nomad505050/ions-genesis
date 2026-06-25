"""
IONS Genesis v0.3 — Deduplication API
Endpoints for CBB embedding migration, duplicate queue, and resolution.
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.services.deduplication import (
    embed_all_cbbs,
    get_duplicate_queue,
    resolve_duplicate,
)
from typing import Dict
import uuid

router = APIRouter(prefix="/dedup", tags=["deduplication"])

# In-memory job tracking
dedup_jobs: Dict[str, dict] = {}


@router.post("/embed")
async def start_embed_cbbs(background_tasks: BackgroundTasks):
    """
    Start background job to embed all existing CBBs.
    Run once after migration. New CBBs are embedded automatically on creation.
    """
    job_id = uuid.uuid4().hex[:8]
    dedup_jobs[job_id] = {"status": "running", "message": "Embedding CBBs...", "embedded": 0, "total": 0}
    background_tasks.add_task(_run_embed_cbbs, job_id)
    return {"job_id": job_id, "status": "running"}


async def _run_embed_cbbs(job_id: str):
    from app.core.database import AsyncSessionLocal
    import traceback
    async with AsyncSessionLocal() as db:
        try:
            result = await embed_all_cbbs(db)
            dedup_jobs[job_id] = {"status": "done", **result}
        except Exception as e:
            dedup_jobs[job_id] = {
                "status": "error",
                "message": str(e),
                "trace": traceback.format_exc()
            }


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Poll for dedup job status."""
    job = dedup_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/status")
async def get_dedup_status(db: AsyncSession = Depends(get_db)):
    """Return current deduplication status."""
    result = await db.execute(text("""
        SELECT
            (SELECT COUNT(*) FROM cbb WHERE status = 'published') as total_cbbs,
            (SELECT COUNT(*) FROM cbb WHERE status = 'published' AND embedding IS NOT NULL) as embedded_cbbs,
            (SELECT COUNT(*) FROM cbb_duplicate_queue WHERE status = 'pending') as pending_review,
            (SELECT COUNT(*) FROM cbb_duplicate_queue WHERE status = 'resolved') as resolved
    """))
    row = result.fetchone()
    return {
        "total_cbbs": row[0],
        "embedded_cbbs": row[1],
        "pending_review": row[2],
        "resolved": row[3],
        "embedding_coverage": round((row[1] / row[0] * 100) if row[0] > 0 else 0, 1),
    }


@router.get("/queue")
async def get_queue(
    status: str = "pending",
    db: AsyncSession = Depends(get_db)
):
    """Get duplicate queue for Workbench review."""
    items = await get_duplicate_queue(db, status=status)
    return items


@router.post("/queue/{queue_id}/resolve")
async def resolve_queue_item(
    queue_id: str,
    resolution: str,  # keep_a | keep_b | keep_both
    db: AsyncSession = Depends(get_db)
):
    """Resolve a near-duplicate pair."""
    if resolution not in ("keep_a", "keep_b", "keep_both"):
        raise HTTPException(
            status_code=400,
            detail="resolution must be keep_a, keep_b, or keep_both"
        )
    result = await resolve_duplicate(queue_id, resolution, db)
    return result


@router.get("/similar/{cbb_id}")
async def find_similar(
    cbb_id: str,
    threshold: float = 0.85,
    db: AsyncSession = Depends(get_db)
):
    """Find CBBs semantically similar to a given CBB."""
    # Get the CBB's embedding
    result = await db.execute(
        text("SELECT embedding, domain, content FROM cbb WHERE cbb_id = :id"),
        {"id": cbb_id}
    )
    row = result.fetchone()
    if not row or row[0] is None:
        raise HTTPException(status_code=404, detail="CBB not found or not embedded")

    embedding = row[0]
    domain = row[1]

    # Find similar CBBs in same domain
    similar_result = await db.execute(
        text("""
            SELECT 
                cbb_id,
                content,
                domain,
                confidence,
                1 - (embedding <=> CAST(:e AS vector)) as similarity
            FROM cbb
            WHERE status = 'published'
            AND domain = :d
            AND cbb_id != :id
            AND embedding IS NOT NULL
            AND 1 - (embedding <=> CAST(:e AS vector)) >= :threshold
            ORDER BY embedding <=> CAST(:e AS vector)
            LIMIT 10
        """),
        {"e": str(embedding), "d": domain, "id": cbb_id, "threshold": threshold}
    )
    matches = similar_result.fetchall()

    return [
        {
            "cbb_id": row[0],
            "content": row[1],
            "domain": row[2],
            "confidence": float(row[3]) if row[3] else 0,
            "similarity": round(float(row[4]), 4),
        }
        for row in matches
    ]