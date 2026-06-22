from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.artifacts import CBB, Relationship
from typing import List, Dict, Any

async def discover_starting_cbbs(query: str, db: AsyncSession, top_k: int = 10) -> List[CBB]:
    # Normalize query
    stop_words = {"why", "how", "what", "does", "do", "is", "are", "the", "a", "an", 
                  "for", "in", "of", "to", "and", "or", "that", "this", "it", "with",
                  "many", "some", "most", "might", "can", "could", "would", "should"}
    
    words = [w.strip().lower() for w in query.split() if len(w.strip()) > 2 and w.strip().lower() not in stop_words]
    
    # Also add bigrams for better matching
    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
    search_terms = words + bigrams

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
        
        # Score each term
        score = 0
        for term in search_terms:
            if term in full_text:
                # Exact phrase in content scores higher
                if term in content_lower:
                    score += 2
                else:
                    score += 1
        
        # Semantic expansion — map query concepts to CBB concepts
        semantic_map = {
            "fail": ["fail", "shallow", "discovery", "transformation", "initiative", "operating", "state"],
            "early": ["shallow", "discovery", "operating", "state", "transformation"],
            "initiatives": ["shallow", "discovery", "transformation", "initiative", "operating"],
            "transformation": ["shallow", "discovery", "operating", "state", "transformation", "initiative"],
            "enterprise": ["enterprise", "organizational", "institutional", "operational"],
            "institutional": ["institutional", "memory", "compound", "decisions"],
            "memory": ["memory", "institutional", "compound", "knowledge"],
            "models": ["model", "parameter", "scale", "weight", "interpreter"],
            "rag": ["rag", "retrieval", "chunk", "path", "artifact"],
            "confidence": ["confidence", "evidence", "trust", "creator", "asserted"],
            "reasoning": ["reasoning", "path", "traversal", "inspectable", "composition"],
            "cbb": ["cbb", "building", "block", "atomic", "claim"],
            "lightweight": ["lightweight", "parameter", "scale", "interpreter"],
            "outperform": ["outperform", "emerge", "traversal", "composition"],
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

async def get_relationships_from(cbb_id: str, db: AsyncSession, include_contradictions: bool = False) -> List[Relationship]:
    stmt = select(Relationship).where(
        Relationship.source_cbb_id == cbb_id,
        Relationship.status == "published"
    )
    if not include_contradictions:
        stmt = stmt.where(Relationship.relationship_type != "contradicts")
    result = await db.execute(stmt)
    return result.scalars().all()

async def enumerate_paths(
    start_cbb: CBB,
    db: AsyncSession,
    max_depth: int = 5,
    max_branch_factor: int = 20,
    include_contradictions: bool = False
) -> List[Dict]:
    paths = []

    async def dfs(current_cbb_id: str, path_cbbs: List[str], path_rels: List[str], depth: int):
        if depth >= max_depth:
            if len(path_cbbs) > 1:
                paths.append({"cbbs": list(path_cbbs), "rels": list(path_rels)})
            return
        rels = await get_relationships_from(current_cbb_id, db, include_contradictions)
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
            await dfs(next_id, path_cbbs, path_rels, depth + 1)
            path_cbbs.pop()
            path_rels.pop()

    await dfs(start_cbb.cbb_id, [start_cbb.cbb_id], [], 0)
    return paths

def compute_evidence_score(evidence_list: list) -> float:
    if not evidence_list:
        return 0.25
    if len(evidence_list) == 1:
        return 0.50
    if len(evidence_list) >= 2:
        return 0.75
    return 0.50

async def score_path(path: Dict, db: AsyncSession) -> Dict:
    cbb_confidences = []
    rel_confidences = []
    evidence_scores = []

    for cbb_id in path["cbbs"]:
        result = await db.execute(select(CBB).where(CBB.cbb_id == cbb_id))
        cbb = result.scalar_one_or_none()
        if cbb:
            cbb_confidences.append(cbb.confidence)
            evidence_scores.append(compute_evidence_score(cbb.evidence or []))

    for rel_id in path["rels"]:
        result = await db.execute(select(Relationship).where(Relationship.relationship_id == rel_id))
        rel = result.scalar_one_or_none()
        if rel:
            rel_confidences.append(rel.confidence)

    cbb_avg = sum(cbb_confidences) / len(cbb_confidences) if cbb_confidences else 0
    rel_avg = sum(rel_confidences) / len(rel_confidences) if rel_confidences else 1.0
    evidence_avg = sum(evidence_scores) / len(evidence_scores) if evidence_scores else 0.25

    # Depth bonus — reward longer paths up to depth 5
    depth = len(path["cbbs"])
    depth_bonus = min(depth / 5, 1.0)

    # New formula — evidence penalty reduced, depth rewarded
    raw_confidence = cbb_avg * rel_avg * evidence_avg
    path_confidence = (raw_confidence * 0.7) + (cbb_avg * 0.2) + (depth_bonus * 0.1)

    return {
        **path,
        "cbb_avg": round(cbb_avg, 4),
        "rel_avg": round(rel_avg, 4),
        "evidence_avg": round(evidence_avg, 4),
        "path_confidence": round(path_confidence, 4)
    }