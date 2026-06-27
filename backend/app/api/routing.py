"""
IONS v0.4 — Routing API
Cognitive Domain taxonomy, routing sessions, and domain assignment endpoints.
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.core.domains import COGNITIVE_DOMAINS, DOMAIN_AFFINITY, NSI_DOMAIN_MAPPING
from typing import Dict
import uuid

router = APIRouter(prefix="/routing", tags=["routing"])

# In-memory job tracking
routing_jobs: Dict[str, dict] = {}


@router.get("/domains")
async def get_cognitive_domains(db: AsyncSession = Depends(get_db)):
    """Return all Cognitive Domains with routing weights and stats."""
    result = await db.execute(text("""
        SELECT domain_id, label, description, routing_weight,
               decay_tier, nsi_count, cbb_count,
               embedding IS NOT NULL as has_embedding,
               last_updated
        FROM cognitive_domain
        ORDER BY cbb_count DESC
    """))
    rows = result.fetchall()

    if not rows:
        # Return taxonomy from config if DB not yet seeded
        return COGNITIVE_DOMAINS

    return [
        {
            "domain_id": row[0],
            "label": row[1],
            "description": row[2],
            "routing_weight": float(row[3]) if row[3] else 1.0,
            "decay_tier": row[4],
            "nsi_count": row[5] or 0,
            "cbb_count": row[6] or 0,
            "has_embedding": row[7],
            "last_updated": row[8].isoformat() if row[8] else None,
        }
        for row in rows
    ]


@router.get("/domains/affinity")
async def get_domain_affinity():
    """Return the domain affinity matrix."""
    return [
        {
            "domain_a": a,
            "domain_b": b,
            "affinity": score
        }
        for (a, b), score in DOMAIN_AFFINITY.items()
    ]


@router.post("/domains/seed")
async def seed_domains(background_tasks: BackgroundTasks):
    """
    Seed Cognitive Domains and assign NSI clusters.
    Run once after migration. Safe to re-run.
    """
    job_id = uuid.uuid4().hex[:8]
    routing_jobs[job_id] = {"status": "running", "message": "Seeding domains..."}
    background_tasks.add_task(_run_seed, job_id)
    return {"job_id": job_id, "status": "running"}


async def _run_seed(job_id: str):
    from app.core.seed_domains import seed_cognitive_domains
    try:
        await seed_cognitive_domains()
        routing_jobs[job_id] = {"status": "done", "message": "Domains seeded successfully"}
    except Exception as e:
        routing_jobs[job_id] = {"status": "error", "message": str(e)}


@router.get("/domains/jobs/{job_id}")
async def get_seed_job(job_id: str):
    """Poll domain seeding job status."""
    job = routing_jobs.get(job_id)
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/sessions")
async def get_routing_sessions(
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Return recent routing sessions."""
    result = await db.execute(text("""
        SELECT session_id, query, intent, routing_confidence,
               cache_hit, conflicts_detected, created_at
        FROM routing_session
        ORDER BY created_at DESC
        LIMIT :limit
    """), {"limit": limit})
    rows = result.fetchall()
    return [
        {
            "session_id": row[0],
            "query": row[1],
            "intent": row[2],
            "routing_confidence": float(row[3]) if row[3] else None,
            "cache_hit": row[4],
            "conflicts_detected": row[5] or 0,
            "created_at": row[6].isoformat() if row[6] else None,
        }
        for row in rows
    ]


@router.get("/sessions/{session_id}")
async def get_routing_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get full routing session detail — the flight recorder for a query."""
    result = await db.execute(text("""
        SELECT * FROM routing_session WHERE session_id = :id
    """), {"id": session_id})
    row = result.fetchone()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")
    return dict(row._mapping)


@router.get("/health")
async def get_routing_health(db: AsyncSession = Depends(get_db)):
    """
    Routing health metrics — average routing confidence,
    cache hit ratio, conflict rate.
    """
    result = await db.execute(text("""
        SELECT
            COUNT(*) as total_sessions,
            AVG(routing_confidence) as avg_routing_confidence,
            SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::float /
                NULLIF(COUNT(*), 0) as cache_hit_ratio,
            AVG(conflicts_detected) as avg_conflicts,
            MIN(created_at) as earliest,
            MAX(created_at) as latest
        FROM routing_session
        WHERE created_at > now() - interval '7 days'
    """))
    row = result.fetchone()

    domain_result = await db.execute(text("""
        SELECT label, routing_weight
        FROM cognitive_domain
        ORDER BY routing_weight DESC
    """))
    domains = domain_result.fetchall()

    return {
        "window": "7 days",
        "total_sessions": row[0] or 0,
        "avg_routing_confidence": round(float(row[1]), 3) if row[1] else None,
        "cache_hit_ratio": round(float(row[2]), 3) if row[2] else 0,
        "avg_conflicts_per_query": round(float(row[3]), 3) if row[3] else 0,
        "domain_weights": [
            {"label": d[0], "routing_weight": float(d[1])}
            for d in domains
        ],
    }


@router.get("/nsi-assignments")
async def get_nsi_assignments(db: AsyncSession = Depends(get_db)):
    """Show current NSI cluster to Cognitive Domain assignments."""
    result = await db.execute(text("""
        SELECT nc.label, nc.cognitive_domain, nc.cbb_count,
               cd.label as domain_label
        FROM nsi_cluster nc
        LEFT JOIN cognitive_domain cd ON nc.cognitive_domain = cd.domain_id
        ORDER BY nc.cbb_count DESC
    """))
    rows = result.fetchall()
    return [
        {
            "nsi_label": row[0],
            "domain_id": row[1],
            "domain_label": row[3],
            "cbb_count": row[2] or 0,
            "assigned": row[1] is not None,
        }
        for row in rows
    ]


@router.post("/nsi-assignments/{nsi_label}")
async def assign_nsi_to_domain(
    nsi_label: str,
    domain_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Manually assign an NSI cluster to a Cognitive Domain."""
    result = await db.execute(text("""
        UPDATE nsi_cluster
        SET cognitive_domain = :domain_id
        WHERE label = :label
        RETURNING label
    """), {"domain_id": domain_id, "label": nsi_label})
    updated = result.fetchone()
    if not updated:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="NSI cluster not found")
    await db.commit()
    return {"assigned": True, "nsi_label": nsi_label, "domain_id": domain_id}

    # ─── Conflict Artifacts ───────────────────────────────────────

@router.get("/conflicts")
async def get_conflicts(
    resolution: str = "unresolved",
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Get conflict artifacts for Workbench review."""
    from app.services.contradiction import get_conflicts
    return await get_conflicts(db, resolution=resolution, limit=limit)


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: str,
    resolution: str,
    db: AsyncSession = Depends(get_db)
):
    """Curator resolves a conflict — accept_a, accept_b, both_valid, both_invalid."""
    from app.services.contradiction import resolve_conflict
    success = await resolve_conflict(conflict_id, resolution, db)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid resolution or conflict not found")
    return {"resolved": True, "conflict_id": conflict_id, "resolution": resolution}

# ─── Validation ───────────────────────────────────────────────

@router.get("/validation/status")
async def get_validation_status(db: AsyncSession = Depends(get_db)):
    """Return validation metrics for the last 7 days."""
    from app.services.validation import get_validation_status
    return await get_validation_status(db)


@router.get("/validation/history")
async def get_validation_history(
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Recent validation results."""
    result = await db.execute(text("""
        SELECT validation_id, path_id, sample_reason,
               coherence_passed, path_optimal,
               chosen_score, optimality_gap,
               action_taken, validated_at
        FROM path_validation
        ORDER BY validated_at DESC
        LIMIT :limit
    """), {"limit": limit})
    rows = result.fetchall()
    return [
        {
            "validation_id": row[0],
            "path_id": row[1],
            "sample_reason": row[2],
            "coherence_passed": row[3],
            "path_optimal": row[4],
            "chosen_score": float(row[5]) if row[5] else None,
            "optimality_gap": float(row[6]) if row[6] else None,
            "action_taken": row[7],
            "validated_at": row[8].isoformat() if row[8] else None,
        }
        for row in rows
    ]

# ─── CBB Saturation ───────────────────────────────────────────

@router.get("/saturation")
async def get_saturation_report(
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """High-saturation CBBs — potential centralization bottlenecks."""
    from app.services.saturation import get_high_saturation_cbbs
    return await get_high_saturation_cbbs(db, limit=limit)


@router.post("/saturation/update")
async def update_saturation(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Recompute saturation scores for all CBBs."""
    from app.services.saturation import update_saturation_scores
    job_id = uuid.uuid4().hex[:8]
    routing_jobs[job_id] = {"status": "running"}
    background_tasks.add_task(_run_saturation_update, job_id, db)
    return {"job_id": job_id, "status": "running"}


async def _run_saturation_update(job_id: str, db: AsyncSession):
    from app.services.saturation import update_saturation_scores
    result = await update_saturation_scores(db)
    routing_jobs[job_id] = {"status": "done", **result}