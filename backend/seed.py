import asyncio
import uuid
from app.core.database import AsyncSessionLocal
from app.models.artifacts import CBB, Relationship
from app.services.hashing import canonical_hash

CBBS = [
    {"content": "Intelligence can emerge from traversal across many cognitive building blocks rather than from a single stored representation.", "confidence": 0.90, "scope": ["ai_architecture", "cognitive_networks"], "assumptions": ["CBBs are well-structured and connected"]},
    {"content": "Models can act as interpreters of externalized knowledge rather than durable stores of intelligence.", "confidence": 0.88, "scope": ["ai_architecture"], "assumptions": ["Knowledge is externalized into reusable artifacts"]},
    {"content": "Reasoning paths are more inspectable than answers produced without visible composition.", "confidence": 0.85, "scope": ["ai_systems", "explainability"]},
    {"content": "A single CBB is useful but the value of the network emerges through composition.", "confidence": 0.87, "scope": ["cognitive_networks"]},
    {"content": "Shallow discovery is a common cause of failed AI transformation initiatives.", "confidence": 0.82, "scope": ["enterprise_ai", "organizational_transformation"]},
    {"content": "Institutional memory compounds when decisions, rationale, and outcomes remain linked.", "confidence": 0.84, "scope": ["organizational_cognition", "knowledge_management"]},
    {"content": "Operational intelligence requires evidence of how work is actually performed, not just how it is documented.", "confidence": 0.83, "scope": ["enterprise_ai", "operational_discovery"]},
    {"content": "Knowledge graphs store relationships but IONS treats reasoning paths as reusable first-class artifacts.", "confidence": 0.86, "scope": ["ai_architecture", "knowledge_graphs"]},
    {"content": "Confidence must be shown with its path and evidence, not as context-free truth.", "confidence": 0.88, "scope": ["ai_systems", "epistemics"]},
    {"content": "Parameter scale is not the only path to useful intelligence.", "confidence": 0.85, "scope": ["ai_architecture", "model_design"]},
    {"content": "CBBs externalize knowledge that models would otherwise compress into weights.", "confidence": 0.87, "scope": ["ai_architecture", "knowledge_systems"]},
    {"content": "Traversal can begin with bounded path enumeration at small scale.", "confidence": 0.82, "scope": ["cognitive_networks", "traversal"]},
    {"content": "Context dependence requires scope and assumptions to be preserved in every CBB.", "confidence": 0.84, "scope": ["ai_systems", "epistemics"]},
    {"content": "RAG retrieves context but usually discards the reasoning path as a reusable artifact.", "confidence": 0.83, "scope": ["ai_architecture", "retrieval_systems"]},
    {"content": "Reusable reasoning paths can compound knowledge across repeated queries.", "confidence": 0.81, "scope": ["cognitive_networks", "knowledge_systems"]},
    {"content": "Human review is a necessary validation gate in early cognitive network systems.", "confidence": 0.86, "scope": ["ai_systems", "validation"]},
    {"content": "A CBB should contain exactly one claim to remain reusable and evaluable.", "confidence": 0.90, "scope": ["cbb_design"]},
    {"content": "Relationships between CBBs need rationale to be trustworthy in traversal.", "confidence": 0.85, "scope": ["cognitive_networks", "cbb_design"]},
    {"content": "Contradictory relationships should generate alternative reasoning paths not be suppressed.", "confidence": 0.83, "scope": ["traversal", "epistemics"]},
    {"content": "A lightweight model guided by a strong CBB path can outperform a large model answering without context.", "confidence": 0.80, "scope": ["ai_architecture", "model_design"]},
    {"content": "Organizational intelligence degrades when institutional memory is stored only in individuals.", "confidence": 0.85, "scope": ["organizational_cognition"]},
    {"content": "AI transformation fails when the operating state of the organization is not discovered before implementation.", "confidence": 0.84, "scope": ["enterprise_ai", "organizational_transformation"]},
    {"content": "Knowledge without relationships is inert and cannot participate in reasoning.", "confidence": 0.88, "scope": ["cognitive_networks", "knowledge_systems"]},
    {"content": "Cryptographic integrity of a CBB does not imply its validity or truth.", "confidence": 0.87, "scope": ["ai_systems", "validation"]},
    {"content": "Creator-asserted confidence must be separated from network-validated confidence.", "confidence": 0.86, "scope": ["ai_systems", "validation"]},
    {"content": "Genesis should use claim CBBs only to force protocol clarity before expanding types.", "confidence": 0.89, "scope": ["cbb_design", "protocol"]},
    {"content": "The reference implementation of a protocol forces decisions that whitepapers defer.", "confidence": 0.84, "scope": ["protocol", "software_engineering"]},
    {"content": "CBBs are atoms, relationships are bonds, and reasoning paths are molecules of intelligence.", "confidence": 0.88, "scope": ["cognitive_networks", "ai_architecture"]},
    {"content": "Abstraction emerges from traversable structure not from storing abstractions directly.", "confidence": 0.83, "scope": ["ai_architecture", "cognitive_networks"]},
    {"content": "Human intelligence connects experiences across domains through relationships not storage alone.", "confidence": 0.82, "scope": ["cognitive_science", "ai_architecture"]},
]

RELATIONSHIPS = [
    (0, 1, "supports", 0.88, "If intelligence emerges through traversal then models serve as interpreters not stores."),
    (1, 0, "supports", 0.85, "Models as interpreters reinforces that traversal not storage produces intelligence."),
    (0, 3, "supports", 0.87, "Emergence through traversal depends on network composition not single CBBs."),
    (3, 22, "depends_on", 0.86, "Network value through composition requires that knowledge with relationships is not inert."),
    (22, 7, "extends", 0.84, "Knowledge needing relationships extends to IONS treating paths as first-class artifacts."),
    (7, 14, "supports", 0.83, "Treating paths as first-class artifacts enables reusable reasoning path compounding."),
    (14, 2, "supports", 0.85, "Reusable paths compound knowledge and are more inspectable than raw answers."),
    (2, 8, "supports", 0.86, "Inspectable paths require confidence shown with evidence not as context-free truth."),
    (8, 24, "refines", 0.84, "Confidence with evidence refines the separation of creator vs network confidence."),
    (4, 21, "supports", 0.87, "Shallow discovery causes AI failure which compounds when operating state is unknown."),
    (21, 6, "depends_on", 0.85, "AI transformation failure from unknown operating state depends on lack of operational intelligence."),
    (6, 5, "supports", 0.83, "Operational intelligence supports institutional memory compounding through linked decisions."),
    (5, 20, "supports", 0.84, "Institutional memory compounding is undermined when memory lives only in individuals."),
    (9, 10, "supports", 0.86, "Parameter scale not being the only path supports CBBs externalizing compressed knowledge."),
    (10, 1, "supports", 0.88, "Externalizing knowledge into CBBs supports models acting as interpreters."),
    (10, 11, "supports", 0.82, "Externalized knowledge supports bounded traversal at small scale."),
    (11, 0, "supports", 0.84, "Bounded traversal supports intelligence emerging through CBB traversal."),
    (13, 7, "contradicts", 0.78, "RAG discarding paths contradicts IONS treating paths as first-class reusable artifacts."),
    (13, 14, "contradicts", 0.76, "RAG not storing paths contradicts reusable path compounding."),
    (16, 3, "supports", 0.87, "Single-claim CBBs support network value through clean composable units."),
    (17, 3, "supports", 0.85, "Relationships with rationale support trustworthy network composition."),
    (18, 13, "refines", 0.82, "Contradiction paths refine how alternative reasoning should be handled vs suppressed."),
    (19, 0, "supports", 0.83, "Lightweight model with strong CBB path supports intelligence through traversal thesis."),
    (19, 9, "supports", 0.84, "CBB-guided lightweight model supports parameter scale not being the only path."),
    (25, 16, "supports", 0.86, "Genesis claim-only CBBs supports atomic single-claim CBB design rule."),
    (26, 25, "supports", 0.83, "Reference implementation forcing decisions supports Genesis claim-only scope decision."),
    (27, 28, "supports", 0.85, "Atom-bond-molecule framing supports abstraction emerging from traversable structure."),
    (28, 29, "supports", 0.82, "Abstraction from structure supports human intelligence connecting via relationships."),
    (29, 0, "supports", 0.84, "Human relational intelligence supports the IONS traversal emergence thesis."),
    (12, 8, "supports", 0.85, "Scope and assumptions in CBBs support confidence being shown with context not as universal truth."),
]

async def seed():
    async with AsyncSessionLocal() as db:
        print("Seeding CBBs...")
        cbb_ids = []
        for i, cbb_data in enumerate(CBBS):
            cbb_id = f"cbb_seed_{i:03d}"
            data = {
                "type": "claim",
                "domain": "ai_systems_org_cognition",
                "evidence": [{"source_type": "internal_note", "source_id": "ions_tds_v01", "uri": None, "note": None, "visibility": "internal"}],
                "tags": [],
                "status": "published",
                "assumptions": [],
                **cbb_data
            }
            h = canonical_hash({**data, "cbb_id": cbb_id})
            existing = await db.get(CBB, cbb_id)
            if existing:
                cbb_ids.append(cbb_id)
                continue
            cbb = CBB(
                cbb_id=cbb_id,
                creator="genesis_seed",
                version="1.0",
                hash=h,
                **data
            )
            db.add(cbb)
            cbb_ids.append(cbb_id)
        await db.commit()
        print(f"  {len(cbb_ids)} CBBs seeded.")

        print("Seeding Relationships...")
        rel_count = 0
        for src_idx, tgt_idx, rel_type, confidence, rationale in RELATIONSHIPS:
            rel_id = f"rel_seed_{src_idx:03d}_{tgt_idx:03d}"
            existing = await db.get(Relationship, rel_id)
            if existing:
                continue
            data = {
                "source_cbb_id": cbb_ids[src_idx],
                "target_cbb_id": cbb_ids[tgt_idx],
                "relationship_type": rel_type,
                "confidence": confidence,
                "rationale": rationale,
                "status": "published"
            }
            h = canonical_hash({**data, "relationship_id": rel_id})
            rel = Relationship(
                relationship_id=rel_id,
                creator="genesis_seed",
                hash=h,
                **data
            )
            db.add(rel)
            rel_count += 1
        await db.commit()
        print(f"  {rel_count} relationships seeded.")
        print("Seed complete.")

if __name__ == "__main__":
    asyncio.run(seed())