from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.models.artifacts import CBB, Relationship
from app.core.config import settings
from typing import List, Dict, Any, Optional
import math


# ─────────────────────────────────────────────
# EMBEDDING HELPERS
# ─────────────────────────────────────────────

async def get_query_embedding(query: str) -> Optional[List[float]]:
    """Embed the query for semantic routing and CBB discovery."""
    from app.services.embedding import get_embedding
    return await get_embedding(query)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ─────────────────────────────────────────────
# PHASE 4 — EMBEDDING-GUIDED CBB DISCOVERY
# ─────────────────────────────────────────────

async def discover_starting_cbbs(
    query: str,
    db: AsyncSession,
    top_k: int = None,
    query_embedding: Optional[List[float]] = None,
    subdomain_ids: Optional[List[str]] = None,
) -> List[CBB]:
    """
    Discover starting CBBs using embedding similarity.
    Falls back to keyword search if embeddings unavailable.
    """
    if top_k is None:
        top_k = settings.cbb_discovery_top_k

    if query_embedding is None:
        query_embedding = await get_query_embedding(query)

    if query_embedding:
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        # Fallback: search all CBBs by embedding
        try:
            result = await db.execute(text("""
                SELECT cbb_id, content, confidence, domain, evidence,
                       assumptions, scope, tags, creator, status,
                       version, hash, created_at, updated_at,
                       1 - (embedding <=> CAST(:q AS vector)) as similarity
                FROM cbb
                WHERE status = 'published'
                AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:q AS vector)
                LIMIT :k
            """), {"q": embedding_str, "k": top_k})
            rows = result.fetchall()
            if rows:
                return await _rows_to_cbbs(rows, db)
        except Exception as e:
            await db.rollback()

    # Final fallback: legacy keyword search
    return await _discover_cbbs_keyword(query, db, top_k)


async def _rows_to_cbbs(rows, db: AsyncSession) -> List[CBB]:
    """Convert raw DB rows to CBB objects."""
    cbb_ids = [row[0] for row in rows]
    result = await db.execute(
        select(CBB).where(CBB.cbb_id.in_(cbb_ids))
    )
    cbbs = {c.cbb_id: c for c in result.scalars().all()}
    # Preserve similarity ordering
    return [cbbs[cbb_id] for cbb_id in cbb_ids if cbb_id in cbbs]


async def _discover_cbbs_keyword(
    query: str,
    db: AsyncSession,
    top_k: int = 10
) -> List[CBB]:
    """Legacy keyword-based CBB discovery. Used as fallback."""
    stop_words = {
        "why", "how", "what", "does", "do", "is", "are", "the", "a", "an",
        "for", "in", "of", "to", "and", "or", "that", "this", "it", "with",
        "many", "some", "most", "might", "can", "could", "would", "should"
    }
    words = [
        w.strip().lower() for w in query.split()
        if len(w.strip()) > 2 and w.strip().lower() not in stop_words
    ]
    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
    search_terms = words + bigrams

    stmt = select(CBB).where(CBB.status == "published")
    result = await db.execute(stmt)
    all_cbbs = result.scalars().all()

    scored = []
    for cbb in all_cbbs:
        full_text = " ".join([
            cbb.content.lower(),
            (cbb.domain or "").lower(),
            " ".join(cbb.scope or []).lower(),
            " ".join(cbb.assumptions or []).lower(),
        ])
        score = sum(
            2 if term in cbb.content.lower() else 1
            for term in search_terms
            if term in full_text
        )
        if score > 0:
            scored.append((score, cbb))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [cbb for _, cbb in scored[:top_k]]


# ─────────────────────────────────────────────
# PHASE 5 — BEAM SEARCH TRAVERSAL
# ─────────────────────────────────────────────

async def beam_search_traverse(
    start_cbbs: List[CBB],
    db: AsyncSession,
    rel_index: Dict[str, List[Relationship]],
    query_embedding: Optional[List[float]] = None,
    include_contradictions: bool = False,
) -> List[Dict]:
    if not start_cbbs:
        return []
    if not rel_index:
        return []
    
    """
    Beam search traversal guided by query embedding similarity.
    
    v0.4 improvements:
    - Blended extension score (relevance + confidence + evidence + freshness)
    - 4 highest scoring + 1 forced diversity slot per iteration
    - Diversity penalty for paths sharing >60% CBBs
    - Scales to any relationship count
    """

    for cbb in start_cbbs[:3]:
        rels = rel_index.get(cbb.cbb_id, [])

    beam_width = settings.beam_width
    beam_width = settings.beam_width
    diversity_slots = settings.beam_diversity_slots
    max_depth = settings.max_traversal_depth

    # Pre-load CBB embeddings and scores for fast lookup
    cbb_embedding_map: Dict[str, List[float]] = {}
    cbb_confidence_map: Dict[str, float] = {}
    cbb_evidence_map: Dict[str, float] = {}

    # Collect all CBB IDs we might need
    all_candidate_ids = set()
    for cbb in start_cbbs:
        all_candidate_ids.add(cbb.cbb_id)
        for rel in rel_index.get(cbb.cbb_id, []):
            all_candidate_ids.add(rel.target_cbb_id)

    # Load embeddings and scores in chunks
    id_list = list(all_candidate_ids)
    try:
        for i in range(0, len(id_list), 1000):
            chunk = id_list[i:i+1000]
            placeholders = ",".join(f"'{cid}'" for cid in chunk)
            placeholders = ",".join(f"'{cid}'" for cid in chunk)
            result = await db.execute(text(f"""
                SELECT cbb_id, confidence, evidence, embedding
                FROM cbb
                WHERE cbb_id IN ({placeholders})
                AND status = 'published'
            """))
            for row in result.fetchall():
                cbb_id, conf, evidence, emb = row
                cbb_confidence_map[cbb_id] = float(conf) if conf else 0.7
                cbb_evidence_map[cbb_id] = compute_evidence_score(evidence or [])
                if emb is not None:
                    try:
                        if isinstance(emb, str):
                            vals = emb.strip("[]").split(",")
                            cbb_embedding_map[cbb_id] = [float(v) for v in vals]
                        elif isinstance(emb, list):
                            cbb_embedding_map[cbb_id] = emb
                    except Exception:
                        pass
    except Exception:
        await db.rollback()

    # Initialize beams from starting CBBs
    beams = []
    for cbb in start_cbbs:
        sim = cosine_similarity(
            query_embedding or [],
            cbb_embedding_map.get(cbb.cbb_id, [])
        ) if query_embedding else 0.5

        beams.append({
            "cbbs": [cbb.cbb_id],
            "rels": [],
            "score": sim,
            "rel_types": [],
        })

    completed_paths = []

    for depth in range(max_depth):
        candidates = []

        for beam in beams:
            current_id = beam["cbbs"][-1]
            rels = rel_index.get(current_id, [])

            if not include_contradictions:
                rels = [r for r in rels if r.relationship_type != "contradicts"]

            if not rels:
                if len(beam["cbbs"]) > 1:
                    completed_paths.append(beam)
                continue

            for rel in rels:
                next_id = rel.target_cbb_id
                if next_id in beam["cbbs"]:
                    continue  # No cycles

                # Blended extension score
                next_emb = cbb_embedding_map.get(next_id, [])
                query_sim = (
                    cosine_similarity(query_embedding, next_emb)
                    if query_embedding and next_emb else 0.3
                )
                rel_conf = float(rel.confidence) if rel.confidence else 0.5
                cbb_conf = cbb_confidence_map.get(next_id, 0.7)
                evidence = cbb_evidence_map.get(next_id, 0.5)
                freshness = 1.0  # future: domain-tier decay

                ext_score = (
                    query_sim  * settings.beam_query_weight +
                    rel_conf   * settings.beam_rel_conf_weight +
                    cbb_conf   * settings.beam_cbb_conf_weight +
                    evidence   * settings.beam_evidence_weight +
                    freshness  * settings.beam_freshness_weight
                )

                # Running average score
                n = len(beam["cbbs"])
                new_score = (beam["score"] * n + ext_score) / (n + 1)

                candidates.append({
                    "cbbs": beam["cbbs"] + [next_id],
                    "rels": beam["rels"] + [rel.relationship_id],
                    "rel_types": beam["rel_types"] + [rel.relationship_type],
                    "score": new_score,
                })

        if not candidates:
            break

        # Sort by score
        candidates.sort(key=lambda x: x["score"], reverse=True)

        # Apply diversity penalty
        penalized = []
        seen_sets = []
        for cand in candidates:
            cbb_set = frozenset(cand["cbbs"])
            penalty = 0.0
            for seen in seen_sets:
                overlap = len(cbb_set & seen) / max(len(cbb_set), 1)
                if overlap > settings.diversity_overlap_threshold:
                    penalty = settings.diversity_penalty
                    break
            penalized.append({**cand, "score": cand["score"] - penalty})
            seen_sets.append(cbb_set)

        penalized.sort(key=lambda x: x["score"], reverse=True)

        # Select beam_width - diversity_slots top candidates
        top_n = beam_width - diversity_slots
        selected = penalized[:top_n]

        # Fill diversity slots from remaining candidates
        # Pick the one most different from already-selected paths
        remaining = penalized[top_n:]
        if remaining and diversity_slots > 0:
            selected_sets = [frozenset(s["cbbs"]) for s in selected]
            best_diverse = None
            best_diverse_score = -1
            for cand in remaining:
                cbb_set = frozenset(cand["cbbs"])
                min_overlap = min(
                    len(cbb_set & s) / max(len(cbb_set), 1)
                    for s in selected_sets
                ) if selected_sets else 0
                diversity_score = 1 - min_overlap
                if diversity_score > best_diverse_score:
                    best_diverse_score = diversity_score
                    best_diverse = cand
            if best_diverse:
                selected.append(best_diverse)

        beams = selected

    completed_paths.extend(beams)

    # Filter to paths with at least 2 CBBs
    return [p for p in completed_paths if len(p["cbbs"]) > 1]

# ─────────────────────────────────────────────
# LEGACY — DEPTH-FIRST TRAVERSAL (kept as fallback)
# ─────────────────────────────────────────────

async def enumerate_paths(
    start_cbb: CBB,
    db: AsyncSession,
    max_depth: int = 5,
    max_branch_factor: int = 20,
    include_contradictions: bool = False,
    rel_index: Dict[str, List[Relationship]] = None
) -> List[Dict]:
    """Legacy depth-first path enumeration. Used as fallback."""
    paths = []

    def dfs(current_id, path_cbbs, path_rels, depth):
        if depth >= max_depth:
            if len(path_cbbs) > 1:
                paths.append({"cbbs": list(path_cbbs), "rels": list(path_rels)})
            return
        rels = rel_index.get(current_id, [])
        if not include_contradictions:
            rels = [r for r in rels if r.relationship_type != "contradicts"]
        rels = rels[:max_branch_factor]
        if not rels:
            if len(path_cbbs) > 1:
                paths.append({"cbbs": list(path_cbbs), "rels": list(path_rels)})
            return
        for rel in rels:
            next_id = rel.target_cbb_id
            if next_id in path_cbbs:
                continue
            path_cbbs.append(next_id)
            path_rels.append(rel.relationship_id)
            dfs(next_id, path_cbbs, path_rels, depth + 1)
            path_cbbs.pop()
            path_rels.pop()

    dfs(start_cbb.cbb_id, [start_cbb.cbb_id], [], 0)
    return paths


# ─────────────────────────────────────────────
# RELATIONSHIP INDEX
# ─────────────────────────────────────────────

async def get_all_published_relationships(
    db: AsyncSession
) -> Dict[str, List[Relationship]]:
    """Load ALL published relationships once and index by source_cbb_id."""
    stmt = select(Relationship).where(Relationship.status == "published")
    result = await db.execute(stmt)
    rels = result.scalars().all()

    index: Dict[str, List[Relationship]] = {}
    for rel in rels:
        if rel.source_cbb_id not in index:
            index[rel.source_cbb_id] = []
        index[rel.source_cbb_id].append(rel)

    return index


# ─────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────

def compute_evidence_score(evidence_list: list) -> float:
    """Score evidence quality for a CBB."""
    if not evidence_list:
        return 0.25
    source_types = [
        e.get("source_type", "") if isinstance(e, dict) else ""
        for e in evidence_list
    ]
    has_strong = any(
        t in ("book", "paper", "article", "url") for t in source_types
    )
    if has_strong:
        return 0.75 if len(evidence_list) == 1 else 0.90
    if len(evidence_list) == 1:
        return 0.50
    return 0.75


async def score_paths_batch(
    paths: List[Dict],
    db: AsyncSession,
    query_embedding: Optional[List[float]] = None,
) -> List[Dict]:
    """
    Score all paths with batch DB load.
    
    v0.4: Computes path_confidence (existing formula) and
    path_relevance (embedding similarity to query).
    """
    all_cbb_ids = set()
    all_rel_ids = set()
    for path in paths:
        all_cbb_ids.update(path["cbbs"])
        all_rel_ids.update(path["rels"])

    # Batch load CBBs in chunks of 1000
    cbb_map: Dict[str, CBB] = {}
    if all_cbb_ids:
        cbb_id_list = list(all_cbb_ids)
        for i in range(0, len(cbb_id_list), 1000):
            chunk = cbb_id_list[i:i+1000]
            result = await db.execute(
                select(CBB).where(CBB.cbb_id.in_(chunk))
            )
            for cbb in result.scalars().all():
                cbb_map[cbb.cbb_id] = cbb

    # Batch load relationships in chunks of 1000
    rel_map: Dict[str, Relationship] = {}
    if all_rel_ids:
        rel_id_list = list(all_rel_ids)
        for i in range(0, len(rel_id_list), 1000):
            chunk = rel_id_list[i:i+1000]
            result = await db.execute(
                select(Relationship).where(Relationship.relationship_id.in_(chunk))
            )
            for rel in result.scalars().all():
                rel_map[rel.relationship_id] = rel

    # Load CBB embeddings for relevance scoring
    cbb_embedding_map: Dict[str, List[float]] = {}
    if query_embedding and all_cbb_ids:
        try:
            cbb_id_list = list(all_cbb_ids)
            for i in range(0, len(cbb_id_list), 1000):
                chunk = cbb_id_list[i:i+1000]
                placeholders = ",".join(f"'{cid}'" for cid in chunk)
                result = await db.execute(text(f"""
                    SELECT cbb_id, embedding FROM cbb
                    WHERE cbb_id IN ({placeholders})
                    AND embedding IS NOT NULL
                """))
                for row in result.fetchall():
                    cbb_id, emb = row
                    if emb is not None:
                        try:
                            if isinstance(emb, str):
                                vals = emb.strip("[]").split(",")
                                cbb_embedding_map[cbb_id] = [float(v) for v in vals]
                            elif isinstance(emb, list):
                                cbb_embedding_map[cbb_id] = emb
                        except Exception:
                            pass
        except Exception as e:
            print(f"DEBUG score embedding error: {e}")
            await db.rollback()

    scored = []
    for path in paths:
        cbb_confidences = []
        rel_confidences = []
        evidence_scores = []
        relevance_scores = []

        for cbb_id in path["cbbs"]:
            cbb = cbb_map.get(cbb_id)
            if cbb:
                cbb_confidences.append(cbb.confidence)
                evidence_scores.append(compute_evidence_score(cbb.evidence or []))

            # Relevance scoring
            if query_embedding:
                emb = cbb_embedding_map.get(cbb_id)
                if emb:
                    relevance_scores.append(cosine_similarity(query_embedding, emb))

        for rel_id in path["rels"]:
            rel = rel_map.get(rel_id)
            if rel:
                rel_confidences.append(rel.confidence)

        cbb_avg = sum(cbb_confidences) / len(cbb_confidences) if cbb_confidences else 0
        rel_avg = sum(rel_confidences) / len(rel_confidences) if rel_confidences else 1.0
        evidence_avg = sum(evidence_scores) / len(evidence_scores) if evidence_scores else 0.25

        depth = len(path["cbbs"])
        depth_bonus = min(depth / 5, 1.0)

        raw_confidence = cbb_avg * rel_avg * evidence_avg
        path_confidence = (raw_confidence * 0.7) + (cbb_avg * 0.2) + (depth_bonus * 0.1)

        # Path relevance — how well path CBBs match the query
        path_relevance = (
            sum(relevance_scores) / len(relevance_scores)
            if relevance_scores else None
        )

        # Path rank score — combines confidence, relevance, utility
        # path_utility defaults to 0.5 until feedback accumulates
        path_utility = path.get("path_utility", 0.5)
        if path_relevance is not None:
            path_rank_score = (
                path_relevance    * settings.rank_relevance_weight +
                path_confidence   * settings.rank_confidence_weight +
                path_utility      * settings.rank_utility_weight
            )
        else:
            path_rank_score = path_confidence

        scored.append({
            **path,
            "cbb_avg": round(cbb_avg, 4),
            "rel_avg": round(rel_avg, 4),
            "evidence_avg": round(evidence_avg, 4),
            "path_confidence": round(path_confidence, 4),
            "path_relevance": round(path_relevance, 4) if path_relevance else None,
            "path_utility": round(path_utility, 4),
            "path_rank_score": round(path_rank_score, 4),
        })

    return scored


async def score_path(path: Dict, db: AsyncSession) -> Dict:
    """Backward compatibility wrapper."""
    results = await score_paths_batch([path], db)
    return results[0]