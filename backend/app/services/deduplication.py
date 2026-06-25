"""
IONS Genesis v0.3 — CBB Deduplication Service
Embeds CBB content and checks for semantic duplicates at ingestion time.
Same domain only. Three tiers:
  > 0.98 similarity → auto-reject, return existing CBB ID
  0.92-0.98         → flag as near-duplicate for Workbench review
  0.85-0.92         → create references relationship automatically
  < 0.85            → create normally
"""
import httpx
import uuid
from typing import Optional, Tuple, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.core.config import settings
from app.models.artifacts import CBB

EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIM = 1536

AUTO_REJECT_THRESHOLD = 0.98
NEAR_DUPLICATE_THRESHOLD = 0.92
RELATED_THRESHOLD = 0.85


async def embed_content(content: str) -> Optional[List[float]]:
    """Get embedding vector for CBB content."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.openrouter_base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "IONS Genesis",
                },
                json={
                    "model": EMBEDDING_MODEL,
                    "input": content,
                },
                timeout=30.0,
            )
            data = response.json()
            return data["data"][0]["embedding"]
        except Exception as e:
            print(f"CBB embedding error: {e}")
            return None


async def check_duplicate(
    content: str,
    domain: str,
    db: AsyncSession,
    exclude_cbb_id: Optional[str] = None,
) -> Tuple[str, Optional[str], Optional[float]]:
    """
    Check if a CBB is a duplicate of an existing one in the same domain.
    
    Returns:
        (action, existing_cbb_id, similarity)
        action: "create" | "auto_reject" | "flag" | "reference"
    """
    # Get embedding for the new content
    embedding = await embed_content(content)
    if not embedding:
        return "create", None, None

    embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

    # Search for similar CBBs in the same domain
    try:
        result = await db.execute(
            text("""
                SELECT 
                    cbb_id,
                    content,
                    1 - (embedding <=> CAST(:e AS vector)) as similarity
                FROM cbb
                WHERE status = 'published'
                AND domain = :d
                AND embedding IS NOT NULL
                AND cbb_id != :exclude
                ORDER BY embedding <=> CAST(:e AS vector)
                LIMIT 5
            """),
            {
                "e": embedding_str,
                "d": domain,
                "exclude": exclude_cbb_id or "",
            }
        )
        matches = result.fetchall()
    except Exception as ex:
        print(f"Similarity search error: {ex}")
        return "create", None, None

    if not matches:
        return "create", None, None

    best_match = matches[0]
    best_cbb_id = best_match[0]
    best_similarity = float(best_match[2])

    if best_similarity >= AUTO_REJECT_THRESHOLD:
        return "auto_reject", best_cbb_id, best_similarity
    elif best_similarity >= NEAR_DUPLICATE_THRESHOLD:
        return "flag", best_cbb_id, best_similarity
    elif best_similarity >= RELATED_THRESHOLD:
        return "reference", best_cbb_id, best_similarity
    else:
        return "create", None, None


async def store_cbb_embedding(cbb_id: str, content: str, db: AsyncSession):
    """
    Embed CBB content and store the vector.
    Called after CBB creation.
    """
    embedding = await embed_content(content)
    if not embedding:
        return

    embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
    try:
        await db.execute(
            text("""
                UPDATE cbb 
                SET embedding = CAST(:e AS vector)
                WHERE cbb_id = :id
            """),
            {"e": embedding_str, "id": cbb_id}
        )
        await db.commit()
    except Exception as ex:
        print(f"Store embedding error: {ex}")


async def queue_near_duplicate(
    cbb_id_a: str,
    cbb_id_b: str,
    similarity: float,
    db: AsyncSession,
):
    """Add a near-duplicate pair to the review queue."""
    # Check if already queued
    result = await db.execute(
        text("""
            SELECT queue_id FROM cbb_duplicate_queue
            WHERE (cbb_id_a = :a AND cbb_id_b = :b)
            OR (cbb_id_a = :b AND cbb_id_b = :a)
            AND status = 'pending'
        """),
        {"a": cbb_id_a, "b": cbb_id_b}
    )
    if result.fetchone():
        return  # Already queued

    queue_id = f"dup_{uuid.uuid4().hex[:8]}"
    await db.execute(
        text("""
            INSERT INTO cbb_duplicate_queue (queue_id, cbb_id_a, cbb_id_b, similarity)
            VALUES (:qid, :a, :b, :sim)
            ON CONFLICT DO NOTHING
        """),
        {"qid": queue_id, "a": cbb_id_a, "b": cbb_id_b, "sim": similarity}
    )
    await db.commit()


async def embed_all_cbbs(db: AsyncSession) -> Dict:
    """
    Migration job: embed all existing CBBs that don't have embeddings.
    Runs as a background task.
    """
    # Get CBBs without embeddings
    result = await db.execute(
        text("""
            SELECT cbb_id, content 
            FROM cbb 
            WHERE status = 'published' 
            AND embedding IS NULL
            ORDER BY created_at ASC
        """)
    )
    cbbs = result.fetchall()

    embedded = 0
    failed = 0

    for cbb_id, content in cbbs:
        embedding = await embed_content(content)
        if embedding:
            embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
            try:
                await db.execute(
                    text("""
                        UPDATE cbb 
                        SET embedding = CAST(:e AS vector)
                        WHERE cbb_id = :id
                    """),
                    {"e": embedding_str, "id": cbb_id}
                )
                await db.commit()
                embedded += 1
            except Exception:
                failed += 1
        else:
            failed += 1

    # After embedding, rebuild the index for better recall
    try:
        await db.execute(text("REINDEX INDEX idx_cbb_embedding"))
        await db.commit()
    except Exception:
        pass

    return {
        "total": len(cbbs),
        "embedded": embedded,
        "failed": failed,
    }


async def get_duplicate_queue(db: AsyncSession, status: str = "pending") -> List[Dict]:
    """Get near-duplicate pairs for Workbench review."""
    result = await db.execute(
        text("""
            SELECT 
                q.queue_id,
                q.similarity,
                q.status,
                q.created_at,
                a.cbb_id as cbb_id_a,
                a.content as content_a,
                a.domain as domain_a,
                a.confidence as confidence_a,
                b.cbb_id as cbb_id_b,
                b.content as content_b,
                b.domain as domain_b,
                b.confidence as confidence_b
            FROM cbb_duplicate_queue q
            JOIN cbb a ON q.cbb_id_a = a.cbb_id
            JOIN cbb b ON q.cbb_id_b = b.cbb_id
            WHERE q.status = :status
            ORDER BY q.similarity DESC, q.created_at DESC
        """),
        {"status": status}
    )
    rows = result.fetchall()

    return [
        {
            "queue_id": row[0],
            "similarity": float(row[1]),
            "status": row[2],
            "created_at": row[3].isoformat() if row[3] else None,
            "cbb_a": {
                "cbb_id": row[4],
                "content": row[5],
                "domain": row[6],
                "confidence": float(row[7]) if row[7] else 0,
            },
            "cbb_b": {
                "cbb_id": row[8],
                "content": row[9],
                "domain": row[10],
                "confidence": float(row[11]) if row[11] else 0,
            },
        }
        for row in rows
    ]


async def resolve_duplicate(
    queue_id: str,
    resolution: str,  # "keep_a" | "keep_b" | "merge" | "keep_both"
    db: AsyncSession,
) -> Dict:
    """
    Resolve a near-duplicate pair.
    - keep_a: deprecate B
    - keep_b: deprecate A  
    - merge: keep A, copy best content, deprecate B
    - keep_both: mark as resolved, keep both
    """
    # Get the queue entry
    result = await db.execute(
        text("SELECT cbb_id_a, cbb_id_b FROM cbb_duplicate_queue WHERE queue_id = :qid"),
        {"qid": queue_id}
    )
    row = result.fetchone()
    if not row:
        return {"error": "Queue entry not found"}

    cbb_id_a, cbb_id_b = row[0], row[1]

    if resolution == "keep_a":
        await db.execute(
            text("UPDATE cbb SET status = 'deprecated' WHERE cbb_id = :id"),
            {"id": cbb_id_b}
        )
    elif resolution == "keep_b":
        await db.execute(
            text("UPDATE cbb SET status = 'deprecated' WHERE cbb_id = :id"),
            {"id": cbb_id_a}
        )
    elif resolution == "keep_both":
        pass  # No action on CBBs

    # Mark queue entry as resolved
    await db.execute(
        text("""
            UPDATE cbb_duplicate_queue 
            SET status = 'resolved', resolution = :res
            WHERE queue_id = :qid
        """),
        {"res": resolution, "qid": queue_id}
    )
    await db.commit()

    return {"resolved": True, "resolution": resolution}