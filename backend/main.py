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