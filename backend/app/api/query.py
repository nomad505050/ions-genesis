"""
IONS Query Engine — single and multi-node traversal.
Fans out queries to registered nodes, merges and ranks paths.
"""
import uuid
import asyncio
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db
from app.core.config import settings
from app.services.traversal import discover_starting_cbbs, enumerate_paths, score_paths_batch, get_all_published_relationships
from app.services.synthesis import synthesize_answer, raw_llm_answer
from app.services.synthesis import fetch_cbb_contents_batch
from app.services.hashing import canonical_hash
from app.models.artifacts import ReasoningPath, NodeRegistry

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    query: str
    domain: Optional[str] = None
    max_depth: int = 5
    top_n_paths: int = 3
    include_contradictions: bool = False
    model: Optional[str] = None
    save_path: bool = True
    federated: bool = True  # whether to query other registered nodes


async def query_remote_node(node, payload: QueryRequest, model: str) -> List[dict]:
    """Query a remote node and return its paths."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{node.public_api_base.rstrip('/')}/query",
                json={
                    "query": payload.query,
                    "domain": payload.domain,
                    "max_depth": payload.max_depth,
                    "top_n_paths": payload.top_n_paths,
                    "include_contradictions": payload.include_contradictions,
                    "model": model,
                    "save_path": False,
                    "federated": False,  # prevent recursive federation
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                paths = data.get("paths", [])
                for path in paths:
                    path["source_node"] = node.node_id
                    path["source_node_url"] = node.public_api_base
                return paths
    except Exception:
        pass
    return []


@router.post("/query")
async def run_query(payload: QueryRequest, db: AsyncSession = Depends(get_db)):
    model = payload.model or settings.default_model

    # Run raw LLM answer and local traversal
    raw_answer_task = asyncio.create_task(raw_llm_answer(payload.query, model))

    # Local traversal — load relationships once then reuse
    starts = await discover_starting_cbbs(payload.query, db)
    rel_index = await get_all_published_relationships(db)

    all_paths = []
    for start in starts:
        paths = await enumerate_paths(
            start,
            db,
            max_depth=payload.max_depth,
            include_contradictions=payload.include_contradictions,
            rel_index=rel_index
        )
        all_paths.extend(paths)

    # Batch score all paths in two queries instead of N*M queries
    local_scored_raw = await score_paths_batch(all_paths, db)
    local_scored = []
    for scored_path in local_scored_raw:
        scored_path["source_node"] = settings.node_id
        scored_path["source_node_url"] = settings.public_api_base
        local_scored.append(scored_path)

    # Federation — query other registered nodes in parallel
    remote_paths = []
    if payload.federated:
        result = await db.execute(
            select(NodeRegistry).where(
                NodeRegistry.status == "active",
                NodeRegistry.node_id != settings.node_id
            )
        )
        remote_nodes = result.scalars().all()

        if remote_nodes:
            remote_tasks = [
                query_remote_node(node, payload, model)
                for node in remote_nodes
            ]
            remote_results = await asyncio.gather(*remote_tasks, return_exceptions=True)
            for r in remote_results:
                if isinstance(r, list):
                    remote_paths.extend(r)

    # Merge and rank all paths
    all_scored = local_scored + remote_paths
    all_scored.sort(key=lambda x: x.get("path_confidence", 0), reverse=True)
    top_paths = all_scored[:payload.top_n_paths]

    raw_answer = await raw_answer_task

    if not top_paths:
        return {
            "query": payload.query,
            "model": model,
            "raw_answer": raw_answer,
            "cbb_answer": None,
            "paths": [],
            "nodes_queried": 1,
            "message": "No traversal paths found. Add more CBBs and relationships."
        }

    best_path = top_paths[0]
    cbb_answer = await synthesize_answer(payload.query, best_path, db, model, all_paths=top_paths)

    # Save local paths only
    saved_paths = []
    if payload.save_path:
        for path in top_paths:
            if path.get("source_node", settings.node_id) != settings.node_id:
                continue
            path_id = f"path_{uuid.uuid4().hex[:12]}"
            explanation = f"Path traverses {len(path['cbbs'])} CBBs with confidence {path['path_confidence']}"
            h = canonical_hash({"path_id": path_id, "query": payload.query, "cbbs": path["cbbs"]})
            rp = ReasoningPath(
                path_id=path_id,
                query=payload.query,
                cbb_sequence=path["cbbs"],
                relationship_sequence=path["rels"],
                path_confidence=path["path_confidence"],
                evidence_score=path["evidence_avg"],
                answer=cbb_answer if path == best_path else "",
                path_explanation=explanation,
                model_used=model,
                hash=h
            )
            db.add(rp)
            saved_paths.append(path_id)
        await db.commit()

    nodes_queried = 1 + len(set(p.get("source_node") for p in remote_paths if p.get("source_node")))

    return {
        "query": payload.query,
        "model": model,
        "raw_answer": raw_answer,
        "cbb_answer": cbb_answer,
        "nodes_queried": nodes_queried,
        "paths": [
            {
                "path_id": saved_paths[i] if i < len(saved_paths) else None,
                "cbb_sequence": p.get("cbbs", p.get("cbb_sequence", [])),
                "relationship_sequence": p.get("rels", p.get("relationship_sequence", [])),
                "path_confidence": p.get("path_confidence", 0),
                "cbb_avg": p.get("cbb_avg", 0),
                "rel_avg": p.get("rel_avg", 0),
                "evidence_avg": p.get("evidence_avg", 0),
                "source_node": p.get("source_node", settings.node_id),
                "source_node_url": p.get("source_node_url", settings.public_api_base),
            }
            for i, p in enumerate(top_paths)
        ]
    }


@router.get("/path/{path_id}")
async def get_path(path_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve a saved reasoning path by ID."""
    result = await db.execute(
        select(ReasoningPath).where(ReasoningPath.path_id == path_id)
    )
    path = result.scalar_one_or_none()
    if not path:
        raise HTTPException(status_code=404, detail=f"Path {path_id} not found")
    return {
        "path_id": path.path_id,
        "query": path.query,
        "cbb_sequence": path.cbb_sequence,
        "relationship_sequence": path.relationship_sequence,
        "path_confidence": path.path_confidence,
        "evidence_score": path.evidence_score,
        "answer": path.answer,
        "path_explanation": path.path_explanation,
        "model_used": path.model_used,
        "hash": path.hash,
        "created_at": path.created_at.isoformat() if path.created_at else None,
    }


@router.get("/path")
async def list_paths(
    limit: int = 20,
    offset: int = 0,
    min_confidence: Optional[float] = None,
    db: AsyncSession = Depends(get_db)
):
    """List saved reasoning paths, newest first."""
    query = select(ReasoningPath).order_by(desc(ReasoningPath.created_at))
    if min_confidence is not None:
        query = query.where(ReasoningPath.path_confidence >= min_confidence)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    paths = result.scalars().all()
    return [
        {
            "path_id": p.path_id,
            "query": p.query,
            "path_confidence": p.path_confidence,
            "evidence_score": p.evidence_score,
            "cbb_sequence": p.cbb_sequence,
            "answer": p.answer[:200] + "..." if p.answer and len(p.answer) > 200 else p.answer,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in paths
    ]