import httpx
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.artifacts import CBB, Relationship
from typing import List, Dict

async def fetch_cbb_contents_batch(cbb_ids: List[str], db: AsyncSession) -> List[Dict]:
    """Batch load all CBBs in one query instead of N individual queries."""
    if not cbb_ids:
        return []
    result = await db.execute(
        select(CBB).where(CBB.cbb_id.in_(cbb_ids))
    )
    cbb_map = {cbb.cbb_id: cbb for cbb in result.scalars().all()}
    # Return in original order
    return [
        {
            "id": cbb_map[cbb_id].cbb_id,
            "content": cbb_map[cbb_id].content,
            "confidence": cbb_map[cbb_id].confidence,
            "domain": cbb_map[cbb_id].domain,
            "evidence": cbb_map[cbb_id].evidence or [],
        }
        for cbb_id in cbb_ids
        if cbb_id in cbb_map
    ]


async def fetch_relationship_contents_batch(rel_ids: List[str], db: AsyncSession) -> List[Dict]:
    """Batch load all relationships in one query."""
    if not rel_ids:
        return []
    result = await db.execute(
        select(Relationship).where(Relationship.relationship_id.in_(rel_ids))
    )
    rel_map = {rel.relationship_id: rel for rel in result.scalars().all()}
    return [
        {
            "id": rel_map[rel_id].relationship_id,
            "type": rel_map[rel_id].relationship_type,
            "rationale": rel_map[rel_id].rationale or "",
            "confidence": rel_map[rel_id].confidence,
        }
        for rel_id in rel_ids
        if rel_id in rel_map
    ]


async def synthesize_answer(query: str, path: Dict, db: AsyncSession, model: str = None, all_paths: List[Dict] = None) -> str:
    """
    Synthesize a rich answer from the best path, with additional context
    from alternative paths where available.
    """
    # Batch load CBBs and relationships
    cbbs = await fetch_cbb_contents_batch(path["cbbs"], db)
    rels = await fetch_relationship_contents_batch(path.get("rels", []), db)

    if not cbbs:
        return "No CBB content available to synthesize an answer."

    # Build the reasoning chain with relationship types
    chain_parts = []
    for i, cbb in enumerate(cbbs):
        chain_parts.append(f"[{cbb['id'][:8]}] ({cbb['domain']}, confidence {cbb['confidence']}): {cbb['content']}")
        if i < len(rels):
            rel = rels[i]
            chain_parts.append(f"  → [{rel['type'].upper()}] {rel['rationale']}")

    chain_text = "\n".join(chain_parts)

    # Include alternative path CBBs as supplementary context
    alt_context = ""
    if all_paths and len(all_paths) > 1:
        alt_cbb_ids = []
        for alt_path in all_paths[1:3]:  # top 2 alternative paths
            for cbb_id in alt_path.get("cbbs", []):
                if cbb_id not in path["cbbs"]:
                    alt_cbb_ids.append(cbb_id)

        if alt_cbb_ids:
            alt_cbbs = await fetch_cbb_contents_batch(alt_cbb_ids[:10], db)
            if alt_cbbs:
                alt_text = "\n".join([f"- [{c['id'][:8]}]: {c['content']}" for c in alt_cbbs])
                alt_context = f"\n\nSupplementary CBBs from alternative paths:\n{alt_text}"

    prompt = f"""You are the IONS Genesis Synthesis Engine.

Answer the query using the provided Cognitive Building Blocks (CBBs) and their relationships.
Ground every claim in the CBBs provided. Do not introduce unsupported information.
Make the reasoning chain visible — show how each CBB connects to the next.
Use the supplementary CBBs to add depth and nuance where relevant.

Query: {query}

Primary Reasoning Path (confidence {path['path_confidence']}):
{chain_text}
{alt_context}

Provide a structured answer with these sections:

**Concise answer:** 2-3 sentences directly answering the query.

**Reasoning chain:** Step through how each CBB connects to build the answer. Reference CBB IDs in brackets. Stop after covering all CBBs in the primary path.

**Confidence caveat:** If path confidence is below 0.6, state what additional knowledge would strengthen the answer in one sentence.

Stop writing after the confidence caveat. Do not add additional commentary."""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.openrouter_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "IONS Genesis"
            },
            json={
                "model": model or settings.default_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 800
            },
            timeout=60.0  # increased from 30s
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def raw_llm_answer(query: str, model: str = None) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.openrouter_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "IONS Genesis"
            },
            json={
                "model": model or settings.default_model,
                "messages": [{"role": "user", "content": query}],
                "max_tokens": 800
            },
            timeout=30.0
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]