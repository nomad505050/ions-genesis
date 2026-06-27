from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.api.cbbs import router as cbb_router
from app.api.relationships import router as relationship_router
from app.api.query import router as query_router
from app.api.nodes import router as nodes_router
from app.core.database import get_db, engine, Base
from app.core.config import settings
from app.models.artifacts import CBB, NodeRegistry
from app.api.nsi import router as nsi_router
from app.api.dedup import router as dedup_router
from app.api.routing import router as routing_router
from app.api.feedback import router as feedback_router
from sqlalchemy import text

app = FastAPI(
    title="IONS Genesis API",
    description="Intelligence Operating Network System — CBB traversal node",
    version="0.4.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Open protocol — any origin can query
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cbb_router)
app.include_router(relationship_router)
app.include_router(query_router)
app.include_router(nodes_router)
app.include_router(nsi_router)
app.include_router(dedup_router)
app.include_router(routing_router)
app.include_router(feedback_router)

@app.on_event("startup")
async def startup():
    """Create any missing tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health")
async def health():
    return {"status": "ok", "node": settings.node_id}


@app.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)):
    """Live network statistics."""
    from sqlalchemy import func, select
    from app.models.artifacts import CBB, Relationship, NodeRegistry

    cbb_count = await db.scalar(
        select(func.count()).select_from(CBB).where(CBB.status == "published")
    )
    rel_count = await db.scalar(
        select(func.count()).select_from(Relationship).where(Relationship.status == "published")
    )
    node_count = await db.scalar(
        select(func.count()).select_from(NodeRegistry).where(NodeRegistry.status == "active")
    )

    return {
        "published_cbbs": cbb_count or 0,
        "published_relationships": rel_count or 0,
        "active_nodes": (node_count or 0) + 1,  # +1 for this node
        "node_id": settings.node_id,
    }


@app.get("/.well-known/ions-node.json")
async def node_manifest(db: AsyncSession = Depends(get_db)):
    """
    IONS Node Manifest — published at a well-known URL so other nodes
    and routing layers can discover this node's capabilities and domains.
    """
    from sqlalchemy import text

    # Get CBB count
    cbb_count = await db.scalar(
        select(func.count()).select_from(CBB).where(CBB.status == "published")
    )

    # Get Cognitive Domains with declared strength
    try:
        domain_result = await db.execute(text("""
            SELECT label, cbb_count, nsi_count, routing_weight
            FROM cognitive_domain
            ORDER BY cbb_count DESC
        """))
        cognitive_domains = [
            {
                "label": row[0],
                "declared_strength": round(float(row[3]) if row[3] else 1.0, 3),
                "cbb_count": row[1] or 0,
                "subdomain_count": row[2] or 0,
            }
            for row in domain_result.fetchall()
        ]
    except Exception:
        cognitive_domains = []

    return {
        "node_id": settings.node_id,
        "protocol_version": "ions-v0.4",
        "supported_cbb_types": ["claim"],
        "supported_relationship_types": [
            "supports", "contradicts", "depends_on", "causes",
            "correlates_with", "extends", "refines", "references"
        ],
        "capabilities": [
            "publish_cbb",
            "publish_relationship",
            "query",
            "traverse",
            "path_registry",
            "node_registry",
            "federated_query",
            "beam_search",
            "cognitive_routing",
            "semantic_deduplication",
            "path_feedback",
            "conflict_detection",
            "self_validation",
        ],
        "cognitive_domains": cognitive_domains,
        "cbb_count": cbb_count or 0,
        "public_api_base": settings.public_api_base,
        "status": "active",
        "open_contributions": True,
        "description": settings.node_description,
        "v04_features": {
            "beam_search": True,
            "cognitive_domains": True,
            "path_feedback": True,
            "conflict_detection": True,
            "self_validation": True,
            "saturation_tracking": True,
        }
    }