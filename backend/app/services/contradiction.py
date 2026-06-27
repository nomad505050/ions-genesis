"""
IONS v0.4 — Contradiction Detection Service
When beam search finds paths supporting contradictory conclusions,
surface a Conflict Artifact rather than silently choosing one.
"""
import uuid
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import settings


# Relationship types that indicate contradiction
CONTRADICTION_TYPES = {"contradicts"}

# Relationship types that indicate support
SUPPORT_TYPES = {"supports", "causes", "extends", "refines", "depends_on"}


def detect_contradicting_paths(
    paths: List[Dict],
    rel_index: Dict,
) -> List[Tuple[Dict, Dict]]:
    """
    Find pairs of paths that contain contradicting relationships.
    Returns list of (path_a, path_b) conflict pairs.
    """
    conflict_pairs = []

    # Build a map of CBB pairs that have contradicts relationships
    contradiction_pairs = set()
    for source_id, rels in rel_index.items():
        for rel in rels:
            if rel.relationship_type == "contradicts":
                contradiction_pairs.add((source_id, rel.target_cbb_id))
                contradiction_pairs.add((rel.target_cbb_id, source_id))

    if not contradiction_pairs:
        return []

    # Check each pair of paths for contradictions
    for i, path_a in enumerate(paths):
        cbbs_a = set(path_a.get("cbbs", []))
        for path_b in paths[i+1:]:
            cbbs_b = set(path_b.get("cbbs", []))
            # Check if any CBB in path_a contradicts any CBB in path_b
            for cbb_a in cbbs_a:
                for cbb_b in cbbs_b:
                    if (cbb_a, cbb_b) in contradiction_pairs:
                        conflict_pairs.append((path_a, path_b))
                        break
                else:
                    continue
                break

    return conflict_pairs


async def create_conflict_artifact(
    query: str,
    intent: str,
    path_a: Dict,
    path_b: Dict,
    db: AsyncSession,
) -> Optional[str]:
    """
    Store a Conflict Artifact when two paths contradict each other.
    Returns the conflict_id.
    """
    conflict_id = f"conf_{uuid.uuid4().hex[:12]}"

    # Extract conclusions from path answers if available
    conclusion_a = path_a.get("answer", "")[:500] if path_a.get("answer") else None
    conclusion_b = path_b.get("answer", "")[:500] if path_b.get("answer") else None

    try:
        await db.execute(text("""
            INSERT INTO conflict_artifact (
                conflict_id, query, intent,
                path_id_a, path_id_b,
                conclusion_a, conclusion_b,
                conflict_type, resolution,
                created_at
            ) VALUES (
                :cid, :q, :intent,
                :pa, :pb,
                :ca, :cb,
                :ctype, 'unresolved',
                now()
            )
        """), {
            "cid": conflict_id,
            "q": query,
            "intent": intent,
            "pa": path_a.get("path_id", "unknown"),
            "pb": path_b.get("path_id", "unknown"),
            "ca": conclusion_a,
            "cb": conclusion_b,
            "ctype": "direct_contradiction",
        })
        await db.commit()
        return conflict_id
    except Exception as e:
        print(f"Conflict artifact creation error: {e}")
        await db.rollback()
        return None


async def get_conflicts(
    db: AsyncSession,
    resolution: str = "unresolved",
    limit: int = 20,
) -> List[Dict]:
    """Get conflict artifacts for Workbench review."""
    result = await db.execute(text("""
        SELECT conflict_id, query, intent,
               path_id_a, path_id_b,
               conclusion_a, conclusion_b,
               conflict_type, resolution,
               created_at
        FROM conflict_artifact
        WHERE resolution = :res
        ORDER BY created_at DESC
        LIMIT :limit
    """), {"res": resolution, "limit": limit})
    rows = result.fetchall()
    return [
        {
            "conflict_id": row[0],
            "query": row[1],
            "intent": row[2],
            "path_id_a": row[3],
            "path_id_b": row[4],
            "conclusion_a": row[5],
            "conclusion_b": row[6],
            "conflict_type": row[7],
            "resolution": row[8],
            "created_at": row[9].isoformat() if row[9] else None,
        }
        for row in rows
    ]


async def resolve_conflict(
    conflict_id: str,
    resolution: str,  # "accept_a" | "accept_b" | "both_valid" | "both_invalid"
    db: AsyncSession,
) -> bool:
    """Curator resolves a conflict."""
    if resolution not in ("accept_a", "accept_b", "both_valid", "both_invalid"):
        return False
    try:
        await db.execute(text("""
            UPDATE conflict_artifact
            SET resolution = :res
            WHERE conflict_id = :cid
        """), {"res": resolution, "cid": conflict_id})
        await db.commit()
        return True
    except Exception:
        await db.rollback()
        return False


def format_conflict_response(
    conflict_pairs: List[Tuple[Dict, Dict]],
    top_paths: List[Dict],
) -> Dict:
    """
    Format conflict information for inclusion in query response.
    Returns a structured conflict summary.
    """
    if not conflict_pairs:
        return {"conflicts_detected": 0, "conflicts": []}

    conflicts = []
    for path_a, path_b in conflict_pairs[:3]:  # Max 3 conflicts in response
        conflicts.append({
            "path_a_cbbs": path_a.get("cbbs", [])[:3],
            "path_b_cbbs": path_b.get("cbbs", [])[:3],
            "path_a_confidence": path_a.get("path_confidence", 0),
            "path_b_confidence": path_b.get("path_confidence", 0),
            "message": "The network holds two positions on this query. "
                      "Both reasoning chains are shown above.",
        })

    return {
        "conflicts_detected": len(conflict_pairs),
        "conflicts": conflicts,
    }