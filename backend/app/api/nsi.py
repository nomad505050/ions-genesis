"""
IONS Genesis v0.2 — NSI Clustering API
Endpoints for domain embedding, NSI clustering, and cluster retrieval.
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.embedding import (
    embed_all_domains,
    run_nsi_clustering,
    get_nsi_clusters,
)
from typing import Dict

router = APIRouter(prefix="/nsi", tags=["nsi"])

# Simple in-memory job tracking
nsi_jobs: Dict[str, dict] = {}


@router.post("/embed")
async def start_embed(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Embed all unregistered domains from the CBB table.
    Run this once after migration, then it's called automatically on CBB creation.
    """
    import uuid
    job_id = uuid.uuid4().hex[:8]
    nsi_jobs[job_id] = {"status": "running", "message": "Embedding domains..."}
    background_tasks.add_task(_run_embed, job_id, db)
    return {"job_id": job_id, "status": "running"}


async def _run_embed(job_id: str, db: AsyncSession):
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        try:
            result = await embed_all_domains(session)
            nsi_jobs[job_id] = {"status": "done", **result}
        except Exception as e:
            nsi_jobs[job_id] = {"status": "error", "message": str(e)}


@router.post("/cluster")
async def start_cluster(background_tasks: BackgroundTasks):
    """
    Run HDBSCAN clustering on all embedded domains.
    Labels each cluster with LLM. Stores results server-side.
    """
    import uuid
    job_id = uuid.uuid4().hex[:8]
    nsi_jobs[job_id] = {"status": "running", "message": "Clustering domains..."}
    background_tasks.add_task(_run_cluster, job_id)
    return {"job_id": job_id, "status": "running"}


async def _run_cluster(job_id: str):
    from app.core.database import AsyncSessionLocal
    import traceback
    async with AsyncSessionLocal() as session:
        try:
            result = await run_nsi_clustering(session)
            nsi_jobs[job_id] = {"status": "done", **result}
        except Exception as e:
            nsi_jobs[job_id] = {"status": "error", "message": str(e), "trace": traceback.format_exc()}


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Poll for embed or cluster job status."""
    job = nsi_jobs.get(job_id)
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/clusters")
async def get_clusters(db: AsyncSession = Depends(get_db)):
    """
    Return all NSI clusters with domain assignments.
    Used by the graph page instead of client-side LLM grouping.
    """
    clusters = await get_nsi_clusters(db)
    return clusters


@router.get("/status")
async def get_nsi_status(db: AsyncSession = Depends(get_db)):
    """Return current clustering status and counts."""
    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT 
          (SELECT COUNT(*) FROM domain_registry) as total_domains,
          (SELECT COUNT(*) FROM domain_registry WHERE embedding IS NOT NULL) as embedded_domains,
          (SELECT COUNT(*) FROM domain_registry WHERE nsi_cluster_id IS NOT NULL) as clustered_domains,
          (SELECT COUNT(*) FROM nsi_cluster) as total_clusters,
          (SELECT MAX(last_clustered) FROM nsi_cluster) as last_clustered
    """))
    row = result.fetchone()
    return {
        "total_domains": row[0],
        "embedded_domains": row[1],
        "clustered_domains": row[2],
        "total_clusters": row[3],
        "last_clustered": row[4].isoformat() if row[4] else None,
        "ready": row[3] > 0,
    }