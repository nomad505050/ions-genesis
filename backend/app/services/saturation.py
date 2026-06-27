"""
IONS v0.4 — CBB Saturation Tracking
Detects centralization — CBBs appearing in too high a fraction of answers.
Applies a small score penalty to over-saturated CBBs to encourage
alternate reasoning paths. Similar to PageRank damping.
"""
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import settings


async def update_cbb_appearance_counts(
    cbb_ids: List[str],
    db: AsyncSession,
) -> None:
    """
    Increment appearance count for CBBs used in a query result.
    Called after every query that produces paths.
    """
    if not cbb_ids:
        return
    try:
        placeholders = ",".join(f"'{cid}'" for cid in cbb_ids)
        await db.execute(text(f"""
            UPDATE cbb
            SET query_appearance_count = COALESCE(query_appearance_count, 0) + 1
            WHERE cbb_id IN ({placeholders})
        """))
    except Exception as e:
        print(f"Saturation count update error: {e}")
        await db.rollback()


async def update_saturation_scores(db: AsyncSession) -> Dict:
    """
    Recompute saturation scores for all CBBs.
    saturation_score = query_appearance_count / total_queries_in_window
    Run periodically — not on every query.
    """
    try:
        # Get total query count from routing sessions (last 30 days)
        result = await db.execute(text("""
            SELECT COUNT(*) FROM routing_session
            WHERE created_at > now() - interval '30 days'
        """))
        total_queries = result.fetchone()[0] or 1

        # Update saturation scores
        await db.execute(text("""
            UPDATE cbb
            SET saturation_score = LEAST(1.0,
                COALESCE(query_appearance_count, 0)::float / :total
            )
            WHERE status = 'published'
        """), {"total": total_queries})

        await db.commit()

        # Return stats on high-saturation CBBs
        result = await db.execute(text("""
            SELECT COUNT(*) FROM cbb
            WHERE saturation_score > :threshold
            AND status = 'published'
        """), {"threshold": settings.saturation_threshold})
        high_sat_count = result.fetchone()[0] or 0

        return {
            "total_queries": total_queries,
            "high_saturation_cbbs": high_sat_count,
            "threshold": settings.saturation_threshold,
        }
    except Exception as e:
        await db.rollback()
        return {"error": str(e)}


def apply_saturation_penalty(
    scored_paths: List[Dict],
    saturation_map: Dict[str, float],
) -> List[Dict]:
    """
    Apply saturation penalty to paths containing over-saturated CBBs.
    Penalty reduces path_rank_score to encourage alternate paths.
    Only applies when saturation_score exceeds threshold.
    """
    if not saturation_map:
        return scored_paths

    penalized = []
    for path in scored_paths:
        cbb_ids = path.get("cbbs", [])
        max_saturation = max(
            (saturation_map.get(cid, 0.0) for cid in cbb_ids),
            default=0.0
        )

        penalty = 0.0
        if max_saturation > settings.saturation_threshold:
            # Scale penalty by how far above threshold
            excess = max_saturation - settings.saturation_threshold
            penalty = min(settings.saturation_penalty, excess * settings.saturation_penalty)

        if penalty > 0:
            current_rank = path.get("path_rank_score") or path.get("path_confidence", 0)
            path = {
                **path,
                "path_rank_score": round(max(0.1, current_rank - penalty), 4),
                "saturation_penalty_applied": round(penalty, 4),
            }

        penalized.append(path)

    return penalized


async def get_saturation_map(
    cbb_ids: List[str],
    db: AsyncSession,
) -> Dict[str, float]:
    """
    Load saturation scores for a set of CBB IDs.
    Used during scoring to apply penalties.
    """
    if not cbb_ids:
        return {}
    try:
        placeholders = ",".join(f"'{cid}'" for cid in cbb_ids)
        result = await db.execute(text(f"""
            SELECT cbb_id, COALESCE(saturation_score, 0.0)
            FROM cbb
            WHERE cbb_id IN ({placeholders})
        """))
        return {row[0]: float(row[1]) for row in result.fetchall()}
    except Exception:
        return {}


async def get_high_saturation_cbbs(
    db: AsyncSession,
    limit: int = 20,
) -> List[Dict]:
    """
    Return CBBs with saturation above threshold for Workbench review.
    High saturation may indicate centralization bottleneck.
    """
    try:
        result = await db.execute(text("""
            SELECT cbb_id, content, domain,
                   saturation_score, query_appearance_count,
                   confidence
            FROM cbb
            WHERE saturation_score > :threshold
            AND status = 'published'
            ORDER BY saturation_score DESC
            LIMIT :limit
        """), {
            "threshold": settings.saturation_threshold,
            "limit": limit,
        })
        rows = result.fetchall()
        return [
            {
                "cbb_id": row[0],
                "content": row[1][:200] + "..." if row[1] and len(row[1]) > 200 else row[1],
                "domain": row[2],
                "saturation_score": round(float(row[3]), 4) if row[3] else 0,
                "appearance_count": row[4] or 0,
                "confidence": float(row[5]) if row[5] else 0,
            }
            for row in rows
        ]
    except Exception:
        return []