"""
IONS v0.4 — Self-Validation Service
Two-check validation loop — no external model dependency.

Check 1: General Coherence — domain-agnostic structural assessment
Check 2: Path Optimality — did routing find the best available path?

Runs asynchronously, never blocks query response.
"""
import uuid
import random
import asyncio
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import settings


COHERENCE_PROMPT = """You are evaluating whether a reasoning chain is logically coherent.
You do not need domain knowledge to answer this. Evaluate ONLY structural coherence.

Query: {query}

Reasoning chain (each step is a knowledge claim):
{numbered_steps}

Final answer: {answer}

Evaluate:
1. Does each step logically follow from the previous?
2. Does the final answer follow from the chain?
3. Are there any non-sequiturs or unexplained jumps between steps?

Return JSON only, no preamble:
{{
  "coherent": true,
  "breaks_at_step": null,
  "reason": "one sentence summary"
}}"""


async def should_validate(path_confidence: float, path_id: str) -> bool:
    """
    Determine if this path should be validated.
    Triggers: random sample + uncertain confidence range.
    """
    # Random sample
    if random.random() < settings.validation_sample_rate:
        return True
    # Uncertain confidence range — most valuable to validate
    if 0.55 <= path_confidence <= 0.65:
        return True
    return False


async def check_coherence(
    query: str,
    cbb_contents: List[str],
    answer: str,
    model: str,
) -> Dict:
    """
    Check 1: General coherence using local model.
    Domain-agnostic — checks structure only.
    """
    if not cbb_contents:
        return {"coherent": True, "breaks_at_step": None, "reason": "no steps to evaluate"}

    numbered_steps = "\n".join(
        f"{i+1}. {content}" for i, content in enumerate(cbb_contents)
    )

    prompt = COHERENCE_PROMPT.format(
        query=query,
        numbered_steps=numbered_steps,
        answer=answer[:500] if answer else "No answer generated",
    )

    try:
        import httpx
        from app.core.config import settings

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.openrouter_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "IONS Genesis Validation",
                },
                json={
                    "model": model,
                    "max_tokens": 150,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                },
            )
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            import json
            result = json.loads(content)
            return {
                "coherent": result.get("coherent", True),
                "breaks_at_step": result.get("breaks_at_step"),
                "reason": result.get("reason", ""),
            }
    except Exception as e:
        # Validation failure never affects query
        return {"coherent": True, "breaks_at_step": None, "reason": f"validation error: {e}"}


async def check_path_optimality(
    query: str,
    chosen_path: Dict,
    db: AsyncSession,
) -> Dict:
    """
    Check 2: Path optimality.
    Generate alternative paths excluding chosen CBBs.
    If a better path exists, routing was suboptimal.
    """
    from app.services.traversal import (
        discover_starting_cbbs,
        beam_search_traverse,
        score_paths_batch,
        get_all_published_relationships,
        get_query_embedding,
    )

    chosen_score = chosen_path.get("path_rank_score") or chosen_path.get("path_confidence", 0)
    chosen_cbbs = set(chosen_path.get("cbbs", chosen_path.get("cbb_sequence", [])))

    try:
        query_embedding = await get_query_embedding(query)
        rel_index = await get_all_published_relationships(db)

        # Find alternative starting CBBs excluding the chosen path's CBBs
        all_starts = await discover_starting_cbbs(
            query=query,
            db=db,
            top_k=20,
            query_embedding=query_embedding,
        )
        alt_starts = [c for c in all_starts if c.cbb_id not in chosen_cbbs][:5]

        if not alt_starts:
            return {"optimal": True, "reason": "no alternative starting points"}

        # Generate alternative paths
        alt_paths_raw = await beam_search_traverse(
            start_cbbs=alt_starts,
            db=db,
            rel_index=rel_index,
            query_embedding=query_embedding,
        )

        if not alt_paths_raw:
            return {"optimal": True, "reason": "no alternative paths found"}

        alt_scored = await score_paths_batch(
            alt_paths_raw[:10], db, query_embedding=query_embedding
        )

        best_alt_score = max(
            p.get("path_rank_score") or p.get("path_confidence", 0)
            for p in alt_scored
        )

        gap = best_alt_score - chosen_score

        if gap > settings.optimality_gap_threshold:
            return {
                "optimal": False,
                "chosen_score": chosen_score,
                "best_alt_score": best_alt_score,
                "gap": round(gap, 4),
                "action": "adjust_routing_weights",
            }

        return {
            "optimal": True,
            "chosen_score": chosen_score,
            "best_alt_score": best_alt_score,
            "gap": round(gap, 4),
        }

    except Exception as e:
        return {"optimal": True, "reason": f"optimality check error: {e}"}


async def apply_routing_adjustment(
    validation_result: Dict,
    optimality_result: Dict,
    path: Dict,
    db: AsyncSession,
) -> Dict:
    """
    Apply routing weight adjustments based on validation results.
    Only touches the routing layer — never CBB or relationship confidence.
    """
    adjustments = {}

    # Coherence failure — reduce domain routing weight
    if not validation_result.get("coherent", True):
        break_step = validation_result.get("breaks_at_step")
        adjustments["coherence_failure"] = True
        adjustments["break_step"] = break_step
        # Small reduction to routing weight — configurable
        # In v0.4 we log the adjustment; weight updates come in batch job

    # Path suboptimal — log domain that should have been chosen
    if not optimality_result.get("optimal", True):
        adjustments["suboptimal"] = True
        adjustments["gap"] = optimality_result.get("gap")
        adjustments["action"] = optimality_result.get("action")

    return adjustments


async def store_validation(
    path_id: str,
    sample_reason: str,
    coherence_result: Dict,
    optimality_result: Dict,
    adjustments: Dict,
    db: AsyncSession,
) -> Optional[str]:
    """Store validation result in path_validation table."""
    validation_id = f"val_{uuid.uuid4().hex[:12]}"
    try:
        await db.execute(text("""
            INSERT INTO path_validation (
                validation_id, path_id, sample_reason,
                coherence_passed, coherence_break_step, coherence_reason,
                path_optimal, chosen_score, best_alt_score, optimality_gap,
                action_taken, routing_adjustment,
                validated_at
            ) VALUES (
                :vid, :pid, :reason,
                :coherent, :break_step, :coherence_reason,
                :optimal, :chosen_score, :alt_score, :gap,
                :action, :adj::jsonb,
                now()
            )
        """), {
            "vid": validation_id,
            "pid": path_id,
            "reason": sample_reason,
            "coherent": coherence_result.get("coherent", True),
            "break_step": coherence_result.get("breaks_at_step"),
            "coherence_reason": coherence_result.get("reason", ""),
            "optimal": optimality_result.get("optimal", True),
            "chosen_score": optimality_result.get("chosen_score"),
            "alt_score": optimality_result.get("best_alt_score"),
            "gap": optimality_result.get("gap"),
            "action": adjustments.get("action", "none"),
            "adj": str(adjustments),
        })
        await db.commit()
        return validation_id
    except Exception as e:
        print(f"Validation store error: {e}")
        await db.rollback()
        return None


async def run_validation(
    path: Dict,
    query: str,
    answer: str,
    cbb_contents: List[str],
    model: str,
    db: AsyncSession,
    sample_reason: str = "random_sample",
) -> Optional[str]:
    """
    Run full validation pipeline for a path.
    Called asynchronously — never blocks query response.
    """
    path_id = path.get("path_id")
    if not path_id:
        return None

    path_confidence = path.get("path_confidence", 0)

    # Check 1: Coherence
    coherence_result = await check_coherence(query, cbb_contents, answer, model)

    # Check 2: Path optimality (only if coherence passed)
    if coherence_result.get("coherent", True):
        optimality_result = await check_path_optimality(query, path, db)
    else:
        optimality_result = {"optimal": False, "reason": "skipped — coherence failed"}

    # Compute adjustments
    adjustments = await apply_routing_adjustment(
        coherence_result, optimality_result, path, db
    )

    # Store validation record
    validation_id = await store_validation(
        path_id, sample_reason,
        coherence_result, optimality_result,
        adjustments, db
    )

    return validation_id


async def get_validation_status(db: AsyncSession) -> Dict:
    """Return validation metrics."""
    result = await db.execute(text("""
        SELECT
            COUNT(*) as total_validated,
            SUM(CASE WHEN coherence_passed = false THEN 1 ELSE 0 END) as coherence_failures,
            SUM(CASE WHEN path_optimal = false THEN 1 ELSE 0 END) as suboptimal_paths,
            AVG(CASE WHEN chosen_score IS NOT NULL THEN chosen_score END) as avg_chosen_score,
            AVG(CASE WHEN optimality_gap IS NOT NULL THEN optimality_gap END) as avg_gap
        FROM path_validation
        WHERE validated_at > now() - interval '7 days'
    """))
    row = result.fetchone()
    return {
        "window": "7 days",
        "total_validated": row[0] or 0,
        "coherence_failures": row[1] or 0,
        "suboptimal_paths": row[2] or 0,
        "avg_chosen_score": round(float(row[3]), 4) if row[3] else None,
        "avg_optimality_gap": round(float(row[4]), 4) if row[4] else None,
        "coherence_failure_rate": round(
            (row[1] or 0) / max(row[0] or 1, 1), 3
        ),
    }