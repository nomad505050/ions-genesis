"""
IONS v0.4 — Cognitive Domain Seeder
Populates cognitive_domain table and assigns NSI clusters to domains.
Run once after migration. Safe to re-run — uses upsert.
"""
import asyncio
import uuid
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.core.domains import COGNITIVE_DOMAINS, NSI_DOMAIN_MAPPING
from app.services.embedding import get_embedding


async def seed_cognitive_domains():
    """Insert or update all 7 canonical Cognitive Domains with embeddings."""
    async with AsyncSessionLocal() as db:
        # Ensure clean transaction state
        try:
            await db.rollback()
        except Exception:
            pass
        print("Seeding Cognitive Domains...")

        for domain in COGNITIVE_DOMAINS:
            # Generate embedding from label + description
            embed_text = f"{domain['label']}: {domain['description']}"
            embedding = await get_embedding(embed_text)
            embedding_str = None
            if embedding:
                embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

            if embedding_str:
                await db.execute(text("""
                    INSERT INTO cognitive_domain
                        (domain_id, label, description, routing_weight, decay_tier,
                         nsi_count, cbb_count, embedding)
                    VALUES
                        (:id, :label, :desc, :weight, :tier, 0, 0,
                         CAST(:emb AS vector))
                    ON CONFLICT (domain_id) DO UPDATE SET
                        label = EXCLUDED.label,
                        description = EXCLUDED.description,
                        decay_tier = EXCLUDED.decay_tier,
                        embedding = EXCLUDED.embedding,
                        last_updated = now()
                """), {
                    "id": domain["domain_id"],
                    "label": domain["label"],
                    "desc": domain["description"],
                    "weight": domain["routing_weight"],
                    "tier": domain["decay_tier"],
                    "emb": embedding_str,
                })
            else:
                await db.execute(text("""
                    INSERT INTO cognitive_domain
                        (domain_id, label, description, routing_weight, decay_tier,
                         nsi_count, cbb_count)
                    VALUES
                        (:id, :label, :desc, :weight, :tier, 0, 0)
                    ON CONFLICT (domain_id) DO UPDATE SET
                        label = EXCLUDED.label,
                        description = EXCLUDED.description,
                        decay_tier = EXCLUDED.decay_tier,
                        last_updated = now()
                """), {
                    "id": domain["domain_id"],
                    "label": domain["label"],
                    "desc": domain["description"],
                    "weight": domain["routing_weight"],
                    "tier": domain["decay_tier"],
                })

            await db.commit()
            print(f"  ✓ {domain['label']}")

        print("\nAssigning NSI clusters to Cognitive Domains...")

        # Step 1: Exact label matches from mapping
        for nsi_label, domain_id in NSI_DOMAIN_MAPPING.items():
            result = await db.execute(text("""
                UPDATE nsi_cluster
                SET cognitive_domain = :domain_id
                WHERE label = :label
            """), {"domain_id": domain_id, "label": nsi_label})
            if result.rowcount > 0:
                print(f"  ✓ {nsi_label} → {domain_id}")

        await db.commit()

        # Step 2: Auto-assign unmatched clusters via embedding similarity
        print("\nAuto-assigning unmatched NSI clusters by embedding similarity...")

        # Get unassigned clusters
        unassigned = await db.execute(text("""
            SELECT cluster_id, label FROM nsi_cluster
            WHERE cognitive_domain IS NULL
        """))
        unassigned_rows = unassigned.fetchall()

        if unassigned_rows:
            # Get domain embeddings
            domain_embs = await db.execute(text("""
                SELECT domain_id, label, embedding FROM cognitive_domain
                WHERE embedding IS NOT NULL
            """))
            domains = domain_embs.fetchall()

            for cluster_id, label in unassigned_rows:
                # Embed the cluster label
                cluster_embedding = await get_embedding(label)
                if not cluster_embedding:
                    print(f"  ✗ {label} — could not embed")
                    continue

                # Find most similar domain
                best_domain_id = None
                best_sim = -1
                for domain_id, domain_label, domain_emb in domains:
                    if domain_emb is None:
                        continue
                    # Parse embedding
                    try:
                        if isinstance(domain_emb, str):
                            vals = domain_emb.strip("[]").split(",")
                            demb = [float(v) for v in vals]
                        else:
                            demb = domain_emb
                        # Cosine similarity
                        dot = sum(a*b for a,b in zip(cluster_embedding, demb))
                        mag_a = sum(x*x for x in cluster_embedding) ** 0.5
                        mag_b = sum(x*x for x in demb) ** 0.5
                        sim = dot / (mag_a * mag_b) if mag_a and mag_b else 0
                        if sim > best_sim:
                            best_sim = sim
                            best_domain_id = domain_id
                            best_domain_label = domain_label
                    except Exception:
                        continue

                if best_domain_id:
                    await db.execute(text("""
                        UPDATE nsi_cluster
                        SET cognitive_domain = :domain_id
                        WHERE cluster_id = :cid
                    """), {"domain_id": best_domain_id, "cid": cluster_id})
                    print(f"  ~ {label} → {best_domain_label} (sim: {best_sim:.3f})")

            await db.commit()

        print("\nUpdating Cognitive Domain CBB counts...")
        await db.execute(text("""
            UPDATE cognitive_domain cd
            SET cbb_count = (
                SELECT COALESCE(SUM(nc.cbb_count), 0)
                FROM nsi_cluster nc
                WHERE nc.cognitive_domain = cd.domain_id
            ),
            nsi_count = (
                SELECT COUNT(*)
                FROM nsi_cluster nc
                WHERE nc.cognitive_domain = cd.domain_id
            )
        """))
        await db.commit()

        print("\nCognitive Domain seeding complete.")


async def get_domain_stats():
    """Print current domain assignment status."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT cd.label, cd.decay_tier,
                   cd.nsi_count, cd.cbb_count,
                   cd.embedding IS NOT NULL as has_embedding
            FROM cognitive_domain cd
            ORDER BY cd.cbb_count DESC
        """))
        rows = result.fetchall()
        print(f"\n{'Domain':<35} {'Tier':<8} {'NSIs':<6} {'CBBs':<8} {'Embedded'}")
        print("-" * 70)
        for row in rows:
            print(f"{row[0]:<35} {row[1]:<8} {row[2]:<6} {row[3]:<8} {'✓' if row[4] else '✗'}")


if __name__ == "__main__":
    asyncio.run(seed_cognitive_domains())
    asyncio.run(get_domain_stats())