"""
IONS v0.4 — Path Feedback API
Collects thumbs up/down on reasoning paths.
Feeds into path_utility and routing weight adjustments.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    path_id: str
    rating: int  # 1 = positive, -1 = negative
    query: Optional[str] = ""
    feedback_source: str = "user"


@router.post("")
async def submit_feedback(
    payload: FeedbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """Submit thumbs up/down feedback for a reasoning path."""
    if payload.rating not in (1, -1):
        raise HTTPException(status_code=400, detail="Rating must be 1 or -1")

    feedback_id = f"fb_{uuid.uuid4().hex[:12]}"

    try:
        await db.execute(text("""
            INSERT INTO path_feedback (
                feedback_id, path_id, rating,
                feedback_source, query, created_at
            ) VALUES (
                :fid, :pid, :rating,
                :source, :query, now()
            )
        """), {
            "fid": feedback_id,
            "pid": payload.path_id,
            "rating": payload.rating,
            "source": payload.feedback_source,
            "query": payload.query or "",
        })

        # Update path_utility immediately on feedback
        # Positive: small boost, Negative: larger reduction
        delta = 0.01 if payload.rating == 1 else -0.05
        await db.execute(text("""
            UPDATE reasoning_path
            SET path_utility = GREATEST(0.1, LEAST(0.99,
                COALESCE(path_utility, 0.5) + :delta
            ))
            WHERE path_id = :pid
        """), {"delta": delta, "pid": payload.path_id})

        await db.commit()
        return {
            "feedback_id": feedback_id,
            "path_id": payload.path_id,
            "rating": payload.rating,
            "recorded": True,
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/path/{path_id}")
async def get_path_feedback(
    path_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get feedback summary for a specific path."""
    result = await db.execute(text("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) as positive,
            SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END) as negative,
            AVG(rating::float) as avg_rating
        FROM path_feedback
        WHERE path_id = :pid
    """), {"pid": path_id})
    row = result.fetchone()

    # Get current path utility
    util_result = await db.execute(text("""
        SELECT path_utility, path_confidence, path_rank_score
        FROM reasoning_path WHERE path_id = :pid
    """), {"pid": path_id})
    path_row = util_result.fetchone()

    return {
        "path_id": path_id,
        "total_feedback": row[0] or 0,
        "positive": row[1] or 0,
        "negative": row[2] or 0,
        "avg_rating": round(float(row[3]), 3) if row[3] else None,
        "path_utility": float(path_row[0]) if path_row and path_row[0] else 0.5,
        "path_confidence": float(path_row[1]) if path_row and path_row[1] else None,
        "path_rank_score": float(path_row[2]) if path_row and path_row[2] else None,
    }


@router.get("/recent")
async def get_recent_feedback(
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Get recent feedback entries."""
    result = await db.execute(text("""
        SELECT
            pf.feedback_id, pf.path_id, pf.rating,
            pf.feedback_source, pf.query, pf.created_at,
            rp.path_confidence, rp.path_utility
        FROM path_feedback pf
        LEFT JOIN reasoning_path rp ON pf.path_id = rp.path_id
        ORDER BY pf.created_at DESC
        LIMIT :limit
    """), {"limit": limit})
    rows = result.fetchall()
    return [
        {
            "feedback_id": row[0],
            "path_id": row[1],
            "rating": row[2],
            "feedback_source": row[3],
            "query": row[4],
            "created_at": row[5].isoformat() if row[5] else None,
            "path_confidence": float(row[6]) if row[6] else None,
            "path_utility": float(row[7]) if row[7] else None,
        }
        for row in rows
    ]


@router.get("/stats")
async def get_feedback_stats(db: AsyncSession = Depends(get_db)):
    """Overall feedback statistics."""
    result = await db.execute(text("""
        SELECT
            COUNT(*) as total_feedback,
            SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) as total_positive,
            SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END) as total_negative,
            COUNT(DISTINCT path_id) as paths_with_feedback,
            AVG(rating::float) as overall_avg_rating
        FROM path_feedback
        WHERE created_at > now() - interval '30 days'
    """))
    row = result.fetchone()

    # Paths with high utility
    high_util = await db.execute(text("""
        SELECT COUNT(*) FROM reasoning_path
        WHERE path_utility > 0.70
        AND path_utility IS NOT NULL
    """))
    high_util_count = high_util.fetchone()[0]

    return {
        "window": "30 days",
        "total_feedback": row[0] or 0,
        "total_positive": row[1] or 0,
        "total_negative": row[2] or 0,
        "paths_with_feedback": row[3] or 0,
        "overall_avg_rating": round(float(row[4]), 3) if row[4] else None,
        "high_utility_paths": high_util_count or 0,
    }