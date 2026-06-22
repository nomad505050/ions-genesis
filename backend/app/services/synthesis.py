import httpx
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.artifacts import CBB, Relationship
from typing import List, Dict

async def fetch_cbb_contents(cbb_ids: List[str], db: AsyncSession) -> List[Dict]:
    cbbs = []
    for cbb_id in cbb_ids:
        result = await db.execute(select(CBB).where(CBB.cbb_id == cbb_id))
        cbb = result.scalar_one_or_none()
        if cbb:
            cbbs.append({"id": cbb.cbb_id, "content": cbb.content, "confidence": cbb.confidence})
    return cbbs

async def synthesize_answer(query: str, path: Dict, db: AsyncSession, model: str = None) -> str:
    cbbs = await fetch_cbb_contents(path["cbbs"], db)
    if not cbbs:
        return "No CBB content available to synthesize an answer."

    cbb_text = "\n".join([f"- [{c['id']}] (confidence {c['confidence']}): {c['content']}" for c in cbbs])

    prompt = f"""You are the IONS Genesis Synthesis Engine.
Answer the following query using ONLY the provided Cognitive Building Blocks (CBBs).
Do not introduce unsupported claims.
Make the reasoning visible.
If confidence is low, say so.

Query: {query}

Reasoning Path CBBs:
{cbb_text}

Path confidence: {path['path_confidence']}

Provide:
1. A concise answer
2. A one-sentence reasoning chain showing how the CBBs connect
3. A confidence caveat if path confidence is below 0.6"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.openrouter_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "IONS Genesis"
            },
            json={
                "model": model or settings.default_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500
            },
            timeout=30.0
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]

async def raw_llm_answer(query: str, model: str = None) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.openrouter_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "IONS Genesis"
            },
            json={
                "model": model or settings.default_model,
                "messages": [{"role": "user", "content": query}],
                "max_tokens": 500
            },
            timeout=30.0
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]