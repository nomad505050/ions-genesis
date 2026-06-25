"""
IONS Genesis v0.2 — Embedding Service
Handles domain embedding via OpenRouter and NSI clustering via HDBSCAN.
"""
import httpx
import hashlib
import json
import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from app.core.config import settings


EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIM = 1536


async def get_embedding(text_input: str) -> Optional[List[float]]:
    """Get embedding vector for a text string via OpenRouter."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.openrouter_base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "IONS Genesis",
                },
                json={
                    "model": EMBEDDING_MODEL,
                    "input": text_input,
                },
                timeout=30.0,
            )
            data = response.json()
            return data["data"][0]["embedding"]
        except Exception as e:
            print(f"Embedding error for '{text_input}': {e}")
            return None


async def ensure_domain_registered(domain_name: str, db: AsyncSession):
    """
    Register a domain in the domain_registry if not already present.
    Embeds the domain name and stores the vector.
    Called whenever a new CBB is created.
    """
    if not domain_name:
        return

    # Check if already registered
    result = await db.execute(
        text("SELECT domain_name FROM domain_registry WHERE domain_name = :d"),
        {"d": domain_name}
    )
    existing = result.fetchone()

    if existing:
        # Update CBB count
        await db.execute(
            text("""
                UPDATE domain_registry 
                SET cbb_count = cbb_count + 1, last_updated = now()
                WHERE domain_name = :d
            """),
            {"d": domain_name}
        )
        await db.commit()
        return

    # New domain — get embedding
    embedding = await get_embedding(domain_name)

    if embedding:
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
        await db.execute(
            text("""
                INSERT INTO domain_registry (domain_name, embedding, cbb_count)
                VALUES (:d, CAST(:e AS vector), 1)
                ON CONFLICT (domain_name) DO UPDATE
                SET cbb_count = domain_registry.cbb_count + 1,
                    last_updated = now()
            """),
            {"d": domain_name, "e": embedding_str}
        )
    else:
        # Store without embedding if API fails
        await db.execute(
            text("""
                INSERT INTO domain_registry (domain_name, cbb_count)
                VALUES (:d, 1)
                ON CONFLICT (domain_name) DO UPDATE
                SET cbb_count = domain_registry.cbb_count + 1,
                    last_updated = now()
            """),
            {"d": domain_name}
        )

    await db.commit()


async def embed_all_domains(db: AsyncSession) -> Dict[str, Any]:
    """
    One-time migration: embed all existing domains from CBB table
    that are not yet in domain_registry.
    """
    # Get all unique domains from CBB table
    result = await db.execute(
        text("SELECT DISTINCT domain, COUNT(*) as cnt FROM cbb WHERE status = 'published' GROUP BY domain")
    )
    all_domains = result.fetchall()

    # Get already registered domains
    reg_result = await db.execute(
        text("SELECT domain_name FROM domain_registry")
    )
    registered = {row[0] for row in reg_result.fetchall()}

    to_embed = [(row[0], row[1]) for row in all_domains if row[0] and row[0] not in registered]

    embedded = 0
    failed = 0

    for domain_name, cbb_count in to_embed:
        embedding = await get_embedding(domain_name)
        if embedding:
            embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
            await db.execute(
                text("""
                    INSERT INTO domain_registry (domain_name, embedding, cbb_count)
                    VALUES (:d, CAST(:e AS vector), :c)
                    ON CONFLICT (domain_name) DO UPDATE
                    SET embedding = EXCLUDED.embedding,
                        cbb_count = EXCLUDED.cbb_count,
                        last_updated = now()
                """),
                {"d": domain_name, "e": embedding_str, "c": cbb_count}
            )
            await db.commit()
            embedded += 1
        else:
            failed += 1

    return {
        "total_domains": len(all_domains),
        "newly_embedded": embedded,
        "failed": failed,
        "already_registered": len(registered),
    }


async def run_nsi_clustering(db: AsyncSession) -> Dict[str, Any]:
    """
    Run HDBSCAN clustering on all embedded domains.
    Labels each cluster with an LLM call.
    Stores results in nsi_cluster table and updates domain_registry.
    """
    try:
        import numpy as np
        from sklearn.cluster import HDBSCAN
    except ImportError:
        return {"error": "sklearn not installed. Run: pip install scikit-learn numpy"}

    # Load all embedded domains
    result = await db.execute(
        text("""
            SELECT domain_name, embedding, cbb_count 
            FROM domain_registry 
            WHERE embedding IS NOT NULL
            ORDER BY cbb_count DESC
        """)
    )
    rows = result.fetchall()

    if len(rows) < 5:
        return {"error": "Not enough embedded domains to cluster. Run embed first."}

    domain_names = [row[0] for row in rows]
    cbb_counts = [row[2] for row in rows]
    
    # Parse embeddings — may come back as string or list depending on driver
    parsed_embeddings = []
    for row in rows:
        emb = row[1]
        if isinstance(emb, str):
            import json
            emb = json.loads(emb)
        elif hasattr(emb, 'tolist'):
            emb = emb.tolist()
        else:
            emb = list(emb)
        parsed_embeddings.append(emb)
    
    embeddings = np.array(parsed_embeddings, dtype=np.float32)
    
    # Normalize embeddings so euclidean distance approximates cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)  # avoid divide by zero
    embeddings = embeddings / norms

    # Use k-means — assigns every domain to a cluster, no noise
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    # Find optimal k between 10 and 25
    best_k = 15
    best_score = -1
    n_samples = len(embeddings)
    k_range = range(max(5, min(10, n_samples // 10)), min(25, n_samples // 2))
    
    for k in k_range:
        if k >= n_samples:
            continue
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km_labels = km.fit_predict(embeddings)
        if len(set(km_labels)) < 2:
            continue
        try:
            score = silhouette_score(embeddings, km_labels, sample_size=min(500, n_samples))
            if score > best_score:
                best_score = score
                best_k = k
        except Exception:
            pass

    clusterer = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    raw_labels = clusterer.fit_predict(embeddings)
    labels = [int(l) for l in raw_labels]

    # Group domains by cluster
    clusters: Dict[int, List[str]] = {}
    for domain, label, count in zip(domain_names, labels, cbb_counts):
        label = int(label)
        if label not in clusters:
            clusters[label] = []
        clusters[label].append((domain, count))

    # Label each cluster with LLM
    nsi_colors = [
        "#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
        "#06b6d4", "#84cc16", "#f97316", "#ec4899", "#14b8a6",
        "#a855f7", "#eab308", "#3b82f6", "#22c55e", "#fb923c",
        "#e11d48", "#0ea5e9", "#d946ef", "#65a30d", "#dc2626",
    ]

    color_idx = 0
    created_clusters = 0
    noise_count = 0

    # Clear existing clusters
    await db.execute(text("DELETE FROM nsi_cluster"))
    await db.execute(text("UPDATE domain_registry SET nsi_cluster_id = NULL"))
    await db.commit()

    noise_count = 0  # kmeans assigns all domains
    for cluster_label, domain_list in sorted(clusters.items()):
        domain_names_only = [d[0] for d in domain_list]
        total_cbbs = sum(d[1] for d in domain_list)

        if cluster_label == -1:
            # Noise points — unclustered domains (HDBSCAN only)
            noise_count = len(domain_list)
            cluster_id = "nsi_other"
            label = "Other"
        else:
            # Label this cluster with LLM
            cluster_id = f"nsi_{uuid.uuid4().hex[:8]}"
            label = await label_cluster(domain_names_only)

        # Store cluster
        await db.execute(
            text("""
                INSERT INTO nsi_cluster (cluster_id, label, domain_count, cbb_count, color)
                VALUES (:id, :label, :dc, :cc, :color)
                ON CONFLICT (cluster_id) DO UPDATE
                SET label = EXCLUDED.label,
                    domain_count = EXCLUDED.domain_count,
                    cbb_count = EXCLUDED.cbb_count,
                    last_clustered = now()
            """),
            {
                "id": cluster_id,
                "label": label,
                "dc": len(domain_list),
                "cc": total_cbbs,
                "color": nsi_colors[color_idx % len(nsi_colors)] if cluster_label != -1 else "#64748b",
            }
        )

        # Update domain registry with cluster assignment
        for domain_name, _ in domain_list:
            await db.execute(
                text("UPDATE domain_registry SET nsi_cluster_id = :cid WHERE domain_name = :d"),
                {"cid": cluster_id, "d": domain_name}
            )

        if cluster_label != -1:
            color_idx += 1
            created_clusters += 1

    await db.commit()

    return {
        "clusters_created": created_clusters,
        "domains_clustered": len(domain_names) - noise_count,
        "noise_domains": noise_count,
        "total_domains": len(domain_names),
    }


async def label_cluster(domain_names: List[str]) -> str:
    """Ask LLM to label a cluster of domain names."""
    domain_list = ", ".join(domain_names[:20])  # cap at 20 for context window

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.openrouter_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "IONS Genesis",
                },
                json={
                    "model": settings.default_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"""These knowledge domains have been grouped together by semantic similarity.
Give this cluster a short, clear 2-4 word label that captures what they have in common.
Return ONLY the label, nothing else.

Domains: {domain_list}

Label:"""
                        }
                    ],
                    "max_tokens": 20,
                    "temperature": 0.1,
                },
                timeout=30.0,
            )
            data = response.json()
            label = data["choices"][0]["message"]["content"].strip()
            # Clean up any quotes or extra text
            label = label.strip('"\'').split('\n')[0].strip()
            return label[:50]  # cap length
        except Exception as e:
            print(f"Label cluster error: {e}")
            return "Knowledge Cluster"


async def get_nsi_clusters(db: AsyncSession) -> List[Dict]:
    """
    Return all NSI clusters with their domains for the graph page.
    """
    # Get clusters
    cluster_result = await db.execute(
        text("""
            SELECT cluster_id, label, domain_count, cbb_count, color, last_clustered
            FROM nsi_cluster
            ORDER BY cbb_count DESC
        """)
    )
    clusters = cluster_result.fetchall()

    if not clusters:
        return []

    # Get domain assignments
    domain_result = await db.execute(
        text("""
            SELECT domain_name, nsi_cluster_id, cbb_count
            FROM domain_registry
            WHERE nsi_cluster_id IS NOT NULL
            ORDER BY cbb_count DESC
        """)
    )
    domains = domain_result.fetchall()

    # Group domains by cluster
    domain_map: Dict[str, List] = {}
    for domain_name, cluster_id, count in domains:
        if cluster_id not in domain_map:
            domain_map[cluster_id] = []
        domain_map[cluster_id].append({"domain": domain_name, "cbb_count": count})

    return [
        {
            "cluster_id": row[0],
            "label": row[1],
            "domain_count": row[2],
            "cbb_count": row[3],
            "color": row[4] or "#6366f1",
            "last_clustered": row[5].isoformat() if row[5] else None,
            "domains": domain_map.get(row[0], []),
        }
        for row in clusters
    ]