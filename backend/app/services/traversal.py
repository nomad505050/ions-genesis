from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.artifacts import CBB, Relationship
from typing import List, Dict, Any

async def discover_starting_cbbs(query: str, db: AsyncSession, top_k: int = 10) -> List[CBB]:
    stop_words = {"why", "how", "what", "does", "do", "is", "are", "the", "a", "an",
                  "for", "in", "of", "to", "and", "or", "that", "this", "it", "with",
                  "many", "some", "most", "might", "can", "could", "would", "should"}

    words = [w.strip().lower() for w in query.split() if len(w.strip()) > 2 and w.strip().lower() not in stop_words]
    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
    search_terms = words + bigrams

    # Batch load all published CBBs once
    stmt = select(CBB).where(CBB.status == "published")
    result = await db.execute(stmt)
    all_cbbs = result.scalars().all()

    scored = []
    for cbb in all_cbbs:
        content_lower = cbb.content.lower()
        domain_lower = (cbb.domain or "").lower()
        scope_lower = " ".join(cbb.scope or []).lower()
        assumptions_lower = " ".join(cbb.assumptions or []).lower()
        full_text = f"{content_lower} {domain_lower} {scope_lower} {assumptions_lower}"

        score = 0
        for term in search_terms:
            if term in full_text:
                if term in content_lower:
                    score += 2
                else:
                    score += 1

        semantic_map = {
            "fail": ["fail", "shallow", "discovery", "transformation", "initiative"],
            "early": ["shallow", "discovery", "operating", "state", "transformation"],
            "institutional": ["institutional", "memory", "compound", "decisions"],
            "memory": ["memory", "institutional", "compound", "knowledge"],
            "models": ["model", "parameter", "scale", "weight", "interpreter"],
            "rag": ["rag", "retrieval", "chunk", "path", "artifact"],
            "confidence": ["confidence", "evidence", "trust", "creator"],
            "reasoning": ["reasoning", "path", "traversal", "inspectable"],
            "cbb": ["cbb", "building", "block", "atomic", "claim"],
            "lightweight": ["lightweight", "parameter", "scale", "interpreter"],
        }

        for word in words:
            if word in semantic_map:
                for expansion in semantic_map[word]:
                    if expansion in full_text:
                        score += 1

        if score > 0:
            scored.append((score, cbb))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [cbb for _, cbb in scored[:top_k]]


# Cache relationships per CBB to avoid repeated DB hits during traversal
_rel_cache: Dict[str, List[Relationship]] = {}

async def get_all_published_relationships(db: AsyncSession) -> Dict[str, List[Relationship]]:
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


async def enumerate_paths(
    start_cbb: CBB,
    db: AsyncSession,
    max_depth: int = 5,
    max_branch_factor: int = 20,
    include_contradictions: bool = False,
    rel_index: Dict[str, List[Relationship]] = None
) -> List[Dict]:
    """Enumerate paths using a pre-loaded relationship index."""
    paths = []

    def dfs(current_cbb_id: str, path_cbbs: List[str], path_rels: List[str], depth: int):
        if depth >= max_depth:
            if len(path_cbbs) > 1:
                paths.append({"cbbs": list(path_cbbs), "rels": list(path_rels)})
            return

        rels = rel_index.get(current_cbb_id, [])
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


def compute_evidence_score(evidence_list: list) -> float:
    if not evidence_list:
        return 0.25
    # Check if any evidence is from a book or external source
    source_types = [e.get("source_type", "") if isinstance(e, dict) else "" for e in evidence_list]
    has_book = any(t in ("book", "paper", "article", "url") for t in source_types)
    if has_book:
        return 0.75 if len(evidence_list) == 1 else 0.90
    if len(evidence_list) == 1:
        return 0.50
    return 0.75


async def score_paths_batch(paths: List[Dict], db: AsyncSession) -> List[Dict]:
    """Score all paths with a single batch load of CBBs and relationships."""
    # Collect all unique IDs needed
    all_cbb_ids = set()
    all_rel_ids = set()
    for path in paths:
        all_cbb_ids.update(path["cbbs"])
        all_rel_ids.update(path["rels"])

    # Batch load CBBs
    cbb_map: Dict[str, CBB] = {}
    if all_cbb_ids:
        result = await db.execute(
            select(CBB).where(CBB.cbb_id.in_(list(all_cbb_ids)))
        )
        for cbb in result.scalars().all():
            cbb_map[cbb.cbb_id] = cbb

    # Batch load relationships
    rel_map: Dict[str, Relationship] = {}
    if all_rel_ids:
        result = await db.execute(
            select(Relationship).where(Relationship.relationship_id.in_(list(all_rel_ids)))
        )
        for rel in result.scalars().all():
            rel_map[rel.relationship_id] = rel

    # Score each path using the loaded data
    scored = []
    for path in paths:
        cbb_confidences = []
        rel_confidences = []
        evidence_scores = []

        for cbb_id in path["cbbs"]:
            cbb = cbb_map.get(cbb_id)
            if cbb:
                cbb_confidences.append(cbb.confidence)
                evidence_scores.append(compute_evidence_score(cbb.evidence or []))

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

        scored.append({
            **path,
            "cbb_avg": round(cbb_avg, 4),
            "rel_avg": round(rel_avg, 4),
            "evidence_avg": round(evidence_avg, 4),
            "path_confidence": round(path_confidence, 4)
        })

    return scored


# Keep score_path for backward compatibility
async def score_path(path: Dict, db: AsyncSession) -> Dict:
    results = await score_paths_batch([path], db)
    return results[0]