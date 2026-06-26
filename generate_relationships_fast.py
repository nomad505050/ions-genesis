"""
IONS Genesis — Relationship Generation
Generates relationships between all published CBBs.
"""
import json
import time
import os
import random
import requests

apiURL_URL       = "http://162.243.203.243:8000"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL              = "meta-llama/llama-3.1-8b-instruct"
BATCH_SIZE         = 5   # source CBBs per LLM call
SEED_SIZE          = 15  # target CBBs to compare against per batch
DELAY              = 0.5
MIN_CONFIDENCE     = 0.60

RELATIONSHIP_TYPES = ["supports", "contradicts", "depends_on", "causes",
                      "correlates_with", "extends", "refines", "references"]

SYSTEM_PROMPT = """You are a knowledge graph builder for IONS Genesis.

Given source CBBs and target CBBs, find genuine relationships between them.

Rules:
1. Only suggest relationships with confidence >= 0.60
2. Relationship types: supports, contradicts, depends_on, causes, correlates_with, extends, refines, references
3. Aim for 3-5 relationships per source CBB where genuine connections exist
4. Cross-domain connections are valuable — look for them
5. Return ONLY valid JSON, no markdown, no explanation

Output schema:
{
  "relationships": [
    {
      "source_cbb_id": "cbb_xxx",
      "target_cbb_id": "cbb_yyy",
      "relationship_type": "supports",
      "confidence": 0.8,
      "rationale": "one sentence explaining the connection"
    }
  ]
}"""


def fetch_all_published():
    all_cbbs = []
    offset = 0
    while True:
        resp = requests.get(
            f"{apiURL_URL}/cbb",
            params={"status": "published", "limit": 500, "offset": offset}
        )
        batch = resp.json()
        if not batch:
            break
        all_cbbs.extend(batch)
        if len(batch) < 500:
            break
        offset += 500
    return all_cbbs


def get_existing_pairs():
    # Skip fetching existing pairs — API is slow at scale.
    # Duplicates will be rejected by the database unique constraint.
    return set()


def suggest_batch(source_batch, seed_cbbs):
    sources_text = "\n".join([f"SOURCE {c['cbb_id']}: {c['content'][:150]}" for c in source_batch])
    seeds_text   = "\n".join([f"TARGET {c['cbb_id']}: {c['content'][:150]}" for c in seed_cbbs])

    user_prompt = f"""SOURCE CBBs (find relationships FROM these):
{sources_text}

TARGET CBBs (find relationships TO these):
{seeds_text}

Find all meaningful relationships. Cross-domain connections are valuable.
Confidence >= 0.60. Aim for 3-5 per source CBB."""

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            "max_tokens": 2000,
            "temperature": 0.2,
        },
        timeout=60
    )

    result = resp.json()
    if "choices" not in result:
        print(f"API error: {result}")
        return []
    raw = result["choices"][0]["message"]["content"].strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    first = raw.index("{")
    last  = raw.rindex("}") + 1
    return json.loads(raw[first:last]).get("relationships", [])


def post_relationship(source_id, target_id, rel_type, confidence, rationale):
    payload = {
        "source_cbb_id":   source_id,
        "target_cbb_id":   target_id,
        "relationship_type": rel_type,
        "confidence":      confidence,
        "rationale":       rationale,
        "status":          "published",
    }
    resp = requests.post(f"{apiURL_URL}/relationship", json=payload)
    return resp.status_code in (200, 201)


def main():
    print("=" * 60)
    print("IONS Genesis — Relationship Generation")
    print("=" * 60)

    all_cbbs = fetch_all_published()
    print(f"Published CBBs: {len(all_cbbs)}")

    existing = get_existing_pairs()
    print(f"Existing relationships: {len(existing)}")

    # Find CBBs with fewer than 3 relationships
    connected = {}
    for (src, tgt) in existing:
        connected[src] = connected.get(src, 0) + 1

    underconnected = [c for c in all_cbbs if connected.get(c["cbb_id"], 0) < 3]
    print(f"Under-connected CBBs (< 3 relationships): {len(underconnected)}")

    if not underconnected:
        print("All CBBs are well-connected. Nothing to do.")
        return

    # Shuffle so we don't always process same CBBs first
    random.shuffle(underconnected)

    all_ids = {c["cbb_id"] for c in all_cbbs}

    total_created = 0
    batches = [underconnected[i:i+BATCH_SIZE] for i in range(0, len(underconnected), BATCH_SIZE)]

    print(f"\nProcessing {len(batches)} batches of {BATCH_SIZE} CBBs each...\n")

    for i, batch in enumerate(batches):
        batch_ids = {c["cbb_id"] for c in batch}
        candidates = [c for c in all_cbbs if c["cbb_id"] not in batch_ids]
        seeds = random.sample(candidates, min(SEED_SIZE, len(candidates)))

        print(f"Batch [{i+1}/{len(batches)}] — {len(batch)} sources → {len(seeds)} targets", end=" ... ", flush=True)

        try:
            suggestions = suggest_batch(batch, seeds)
            created = 0
            for s in suggestions:
                src  = s.get("source_cbb_id", "")
                tgt  = s.get("target_cbb_id", "")
                rel  = s.get("relationship_type", "references")
                conf = float(s.get("confidence", 0.75))
                rat  = s.get("rationale", "")

                if rel not in RELATIONSHIP_TYPES:
                    continue
                if (src, tgt) in existing:
                    continue
                if conf < MIN_CONFIDENCE:
                    continue
                if src not in all_ids or tgt not in all_ids:
                    continue
                if src not in batch_ids:
                    continue

                if post_relationship(src, tgt, rel, conf, rat):
                    existing.add((src, tgt))
                    created += 1
                    total_created += 1

            print(f"{created} created (total: {total_created})")

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

        time.sleep(DELAY)

    print(f"\n{'=' * 60}")
    print(f"Done — {total_created} total relationships created")
    print(f"Final relationship count: {len(existing)}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()



