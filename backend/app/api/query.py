"""
IONS Query Engine — v0.4
Embedding-guided discovery, beam search traversal, routing sessions.
"""
import uuid
import asyncio
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db
from app.core.config import settings
from app.services.traversal import (
    discover_starting_cbbs,
    beam_search_traverse,
    score_paths_batch,
    get_all_published_relationships,
    get_query_embedding,
)
from app.services.synthesis import synthesize_answer, raw_llm_answer
from app.services.hashing import canonical_hash
from app.models.artifacts import ReasoningPath, NodeRegistry

from app.services.validation import run_validation, should_validate
from app.services.saturation import (
    update_cbb_appearance_counts,
    get_saturation_map,
    apply_saturation_penalty,
)

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    query: str
    domain: Optional[str] = None
    max_depth: int = 5
    top_n_paths: int = 3
    include_contradictions: bool = False
    model: Optional[str] = None
    save_path: bool = True
    federated: bool = True
    intent: str = "explain"  # v0.4 — reasoning intent


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
                    "federated": False,
                    "intent": payload.intent,
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


async def _save_routing_session(
    db: AsyncSession,
    session_id: str,
    query: str,
    intent: str,
    starts: list,
    top_paths: list,
    remote_paths: list,
    routing_confidence: Optional[float],
    cache_hit: bool = False,
) -> None:
    """Store routing session artifact — the flight recorder for this query."""
    try:
        await db.execute(text("""
            INSERT INTO routing_session (
                session_id, query, intent,
                cbbs_discovered, selected_path_id,
                routing_confidence, cache_hit,
                conflicts_detected, created_at
            ) VALUES (
                :sid, :q, :intent,
                :cbbs, :path_id,
                :rconf, :cache,
                :conflicts, now()
            )
        """), {
            "sid": session_id,
            "q": query,
            "intent": intent,
            "cbbs": [c.cbb_id for c in starts],
            "path_id": top_paths[0].get("path_id") if top_paths else None,
            "rconf": routing_confidence,
            "cache": cache_hit,
            "conflicts": 0,
        })
        await db.commit()
    except Exception as e:
        print(f"Routing session save error: {e}")


def _compute_routing_confidence(top_paths: list) -> Optional[float]:
    """
    Compute routing confidence — did attention allocation succeed?
    routing_confidence = winning_path_rank_score / best_possible_score
    Best possible is approximated as 1.0 for now.
    """
    if not top_paths:
        return None
    winning_score = top_paths[0].get("path_rank_score") or top_paths[0].get("path_confidence", 0)
    # Best possible rank score is 1.0
    return round(min(winning_score / 1.0, 1.0), 4)


@router.post("/query")
async def run_query(payload: QueryRequest, db: AsyncSession = Depends(get_db)):
    model = payload.model or settings.default_model
    session_id = f"rsess_{uuid.uuid4().hex[:12]}"

    # Embed query once — used for CBB discovery, beam search, and relevance scoring
    query_embedding = await get_query_embedding(payload.query)

    # Run raw LLM answer — await it before DB operations to avoid asyncpg concurrency
    raw_answer = await raw_llm_answer(payload.query, model)

    # Load relationship index once — reused across all starting CBBs
    rel_index = await get_all_published_relationships(db)

    # Embedding-guided CBB discovery
    starts = await discover_starting_cbbs(
        query=payload.query,
        db=db,
        query_embedding=query_embedding,
    )

    # Beam search traversal
    all_paths = []
    if starts:
        all_paths = await beam_search_traverse(
            start_cbbs=starts,
            db=db,
            rel_index=rel_index,
            query_embedding=query_embedding,
            include_contradictions=payload.include_contradictions,
        )

    # Score paths — includes path_confidence, path_relevance, path_rank_score
    local_scored_raw = await score_paths_batch(
        all_paths, db, query_embedding=query_embedding
    )

    # Apply saturation penalty to discourage over-central CBBs
    all_path_cbb_ids = list({
        cbb_id
        for path in local_scored_raw
        for cbb_id in path.get("cbbs", [])
    })
    saturation_map = await get_saturation_map(all_path_cbb_ids, db)
    local_scored_raw = apply_saturation_penalty(local_scored_raw, saturation_map)
    local_scored = []
    for scored_path in local_scored_raw:
        scored_path["source_node"] = settings.node_id
        scored_path["source_node_url"] = settings.public_api_base
        local_scored.append(scored_path)

    # Federation — query registered nodes in parallel
    remote_paths = []
    if payload.federated:
        try:
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
        except Exception as e:
            print(f"DEBUG federation error: {e}")
            await db.rollback()

    # Contradiction detection
    conflict_info = {"conflicts_detected": 0, "conflicts": []}
    if payload.include_contradictions and local_scored:
        from app.services.contradiction import (
            detect_contradicting_paths,
            format_conflict_response,
            create_conflict_artifact,
        )
        conflict_pairs = detect_contradicting_paths(local_scored, rel_index)
        conflict_info = format_conflict_response(conflict_pairs, local_scored)
        for path_a, path_b in conflict_pairs[:3]:
            await create_conflict_artifact(
                payload.query, payload.intent, path_a, path_b, db
            )

    # Merge and rank — v0.4 uses path_rank_score, falls back to path_confidence
    all_scored = local_scored + remote_paths
    all_scored.sort(
        key=lambda x: x.get("path_rank_score") or x.get("path_confidence", 0),
        reverse=True
    )
    top_paths = all_scored[:payload.top_n_paths]

    if not top_paths:
        try:
            from app.core.database import AsyncSessionLocal
            import json as _json
            async with AsyncSessionLocal() as rs_db:
                await rs_db.execute(text("""
                    INSERT INTO routing_session (
                        session_id, query, intent,
                        nodes_considered, domains_considered, subdomains_considered,
                        cbbs_discovered, routing_confidence, cache_hit,
                        conflicts_detected, created_at
                    ) VALUES (
                        :sid, :q, :intent,
                        :nodes, :domains, :subdomains,
                        :cbbs, :rconf, :cache,
                        :conflicts, now()
                    )
                """), {
                    "sid": session_id,
                    "q": payload.query,
                    "intent": payload.intent,
                    "nodes": "[]",
                    "domains": "[]",
                    "subdomains": "[]",
                    "cbbs": _json.dumps([c.cbb_id for c in starts]),
                    "rconf": None,
                    "cache": False,
                    "conflicts": 0,
                })
                await rs_db.commit()
        except Exception as e:
            print(f"ROUTING SESSION ERROR (no paths): {e}")

    best_path = top_paths[0]
    # Normalize path keys — beam search uses "cbbs", remote paths use "cbb_sequence"
    def normalize_path(p):
        if "cbbs" not in p and "cbb_sequence" in p:
            p = {**p, "cbbs": p["cbb_sequence"], "rels": p.get("relationship_sequence", [])}
        return p

    best_path = normalize_path(best_path)
    top_paths = [normalize_path(p) for p in top_paths]

    cbb_answer = await synthesize_answer(
        payload.query, best_path, db, model, all_paths=top_paths
    )

    # Compute routing confidence
    routing_confidence = _compute_routing_confidence(top_paths)

    # Save local paths
    saved_paths = []
    if payload.save_path:
        for path in top_paths:
            if path.get("source_node", settings.node_id) != settings.node_id:
                continue
            path_id = f"path_{uuid.uuid4().hex[:12]}"
            explanation = (
                f"Path traverses {len(path['cbbs'])} CBBs "
                f"with confidence {path['path_confidence']}"
            )
            h = canonical_hash({
                "path_id": path_id,
                "query": payload.query,
                "cbbs": path["cbbs"]
            })
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
                hash=h,
                path_utility=path.get("path_utility", 0.5),
                path_relevance=path.get("path_relevance"),
                path_rank_score=path.get("path_rank_score"),
                routing_confidence=routing_confidence,
                intent=payload.intent,
                cache_hit=False,
            )
            db.add(rp)
            try:
                await db.flush()
                await db.commit()
                saved_paths.append(path_id)
                path["path_id"] = path_id
            except Exception as e:
                print(f"DEBUG path save error: {e}")
                await db.rollback()

        # Update CBB appearance counts for saturation tracking
        all_used_cbbs = list({
            cbb_id
            for path in top_paths
            for cbb_id in path.get("cbbs", path.get("cbb_sequence", []))
            if path.get("source_node", settings.node_id) == settings.node_id
        })
        if all_used_cbbs:
            cbbs_copy = list(all_used_cbbs)
            async def _update_saturation(cbbs=cbbs_copy):
                from app.core.database import AsyncSessionLocal
                try:
                    async with AsyncSessionLocal() as bg_db:
                        await update_cbb_appearance_counts(cbbs, bg_db)
                except Exception as e:
                    print(f"Saturation update error: {e}")
            asyncio.create_task(_update_saturation())

        if saved_paths and best_path:
            path_conf = best_path.get("path_confidence", 0)
            if 0.55 <= path_conf <= 0.65:  # validate uncertain paths
                path_copy = {**best_path, "path_id": saved_paths[0]}
                query_copy = payload.query
                answer_copy = cbb_answer or ""
                model_copy = model
                async def _run_validation_bg(p=path_copy, q=query_copy, a=answer_copy, m=model_copy):
                    from app.core.database import AsyncSessionLocal
                    from app.services.synthesis import fetch_cbb_contents_batch
                    try:
                        async with AsyncSessionLocal() as bg_db:
                            cbb_ids = p.get("cbbs", [])
                            cbb_contents_list = []
                            if cbb_ids:
                                placeholders = ",".join(f"'{cid}'" for cid in cbb_ids)
                                result = await bg_db.execute(text(f"""
                                    SELECT cbb_id, content FROM cbb
                                    WHERE cbb_id IN ({placeholders})
                                """))
                                contents = {row[0]: row[1] for row in result.fetchall()}
                                cbb_contents_list = [contents.get(cid, "") for cid in cbb_ids]
                            await run_validation(
                                path=p, query=q, answer=a,
                                cbb_contents=cbb_contents_list,
                                model=m, db=bg_db,
                                sample_reason="uncertain_confidence",
                            )
                    except Exception as e:
                        print(f"Validation error: {e}")
                asyncio.create_task(_run_validation_bg())    
 
    # Save routing session using raw asyncpg to avoid greenlet issues
    async def _save_session():
        import json as _json
        import asyncpg
        import os
        try:
            db_url = os.environ.get("DATABASE_URL", "postgresql://ions:ions@postgres:5432/ions")
            # Convert SQLAlchemy URL to asyncpg URL
            conn_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql://", "postgresql://")
            conn = await asyncpg.connect(conn_url)
            try:
                await conn.execute("""
                    INSERT INTO routing_session (
                        session_id, query, intent,
                        nodes_considered, domains_considered, subdomains_considered,
                        cbbs_discovered, selected_path_id,
                        routing_confidence, cache_hit,
                        conflicts_detected, created_at
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,now())
                """,
                    session_id,
                    payload.query,
                    payload.intent,
                    "[]",
                    "[]",
                    "[]",
                    _json.dumps([c.cbb_id for c in starts]),
                    top_paths[0].get("path_id") if top_paths else None,
                    routing_confidence,
                    False,
                    0,
                )
            finally:
                await conn.close()
        except Exception as e:
            print(f"ROUTING SESSION ERROR: {e}")
    asyncio.create_task(_save_session())

    nodes_queried = 1 + len(
        set(p.get("source_node") for p in remote_paths if p.get("source_node"))
    )

    return {
        "query": payload.query,
        "model": model,
        "raw_answer": raw_answer,
        "cbb_answer": cbb_answer,
        "nodes_queried": nodes_queried,
        "session_id": session_id,
        "routing_confidence": routing_confidence,
        "conflicts": conflict_info,
        "paths": [
            {
                "path_id": p.get("path_id") or (saved_paths[i] if i < len(saved_paths) else None),
                "cbb_sequence": p.get("cbbs", p.get("cbb_sequence", [])),
                "relationship_sequence": p.get("rels", p.get("relationship_sequence", [])),
                "path_confidence": p.get("path_confidence", 0),
                "path_relevance": p.get("path_relevance"),
                "path_rank_score": p.get("path_rank_score"),
                "path_utility": p.get("path_utility", 0.5),
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
        "intent": path.intent,
        "cbb_sequence": path.cbb_sequence,
        "relationship_sequence": path.relationship_sequence,
        "path_confidence": path.path_confidence,
        "path_relevance": path.path_relevance,
        "path_rank_score": path.path_rank_score,
        "path_utility": path.path_utility,
        "routing_confidence": path.routing_confidence,
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
            "intent": p.intent,
            "path_confidence": p.path_confidence,
            "path_relevance": p.path_relevance,
            "path_rank_score": p.path_rank_score,
            "routing_confidence": p.routing_confidence,
            "evidence_score": p.evidence_score,
            "cbb_sequence": p.cbb_sequence,
            "answer": p.answer[:200] + "..." if p.answer and len(p.answer) > 200 else p.answer,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in paths
    ]