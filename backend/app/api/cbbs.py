import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.core.database import get_db
from app.models.artifacts import CBB
from app.models.schemas import CBBCreate, CBBResponse
from app.services.hashing import canonical_hash
from app.services.embedding import ensure_domain_registered
from app.services.deduplication import check_duplicate, store_cbb_embedding, queue_near_duplicate

router = APIRouter(prefix="/cbb", tags=["cbbs"])

@router.post("", response_model=CBBResponse)
async def create_cbb(payload: CBBCreate, db: AsyncSession = Depends(get_db)):
    # Check for duplicates in same domain
    action, existing_id, similarity = await check_duplicate(
        content=payload.content,
        domain=payload.domain,
        db=db,
    )

    if action == "auto_reject":
        # Return existing CBB instead of creating duplicate
        result = await db.execute(select(CBB).where(CBB.cbb_id == existing_id))
        existing = result.scalar_one_or_none()
        if existing:
            existing.duplicate_rejected = True  # signal to caller
            return existing

    cbb_id = f"cbb_{uuid.uuid4().hex[:12]}"
    data = payload.model_dump()
    data["evidence"] = [e.model_dump() for e in payload.evidence]
    h = canonical_hash({**data, "cbb_id": cbb_id})
    cbb = CBB(
        cbb_id=cbb_id,
        creator="genesis_node",
        version="1.0",
        hash=h,
        **data
    )
    db.add(cbb)
    await db.commit()
    await db.refresh(cbb)

    # Post-creation: embed and handle near-duplicates
    try:
        await store_cbb_embedding(cbb_id, payload.content, db)
        if action == "flag" and existing_id:
            await queue_near_duplicate(cbb_id, existing_id, similarity, db)
        elif action == "reference" and existing_id:
            # Auto-create references relationship
            from app.models.artifacts import Relationship
            from app.services.hashing import canonical_hash as ch
            rel_id = f"rel_{uuid.uuid4().hex[:12]}"
            rel_data = {
                "relationship_id": rel_id,
                "source_cbb_id": cbb_id,
                "target_cbb_id": existing_id,
                "relationship_type": "references",
                "confidence": round(similarity, 3),
                "rationale": f"Semantically related claim (similarity: {similarity:.3f})",
                "creator": "genesis_dedup",
                "status": "published",
            }
            rel = Relationship(**rel_data, hash=ch(rel_data))
            db.add(rel)
            await db.commit()
        # Auto-embed domain
        if payload.domain:
            from app.services.embedding import ensure_domain_registered
            await ensure_domain_registered(payload.domain, db)
    except Exception as e:
        print(f"Post-creation processing error: {e}")

    return cbb

@router.get("/{cbb_id}", response_model=CBBResponse)
async def get_cbb(cbb_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CBB).where(CBB.cbb_id == cbb_id))
    cbb = result.scalar_one_or_none()
    if not cbb:
        raise HTTPException(status_code=404, detail="CBB not found")
    return cbb

@router.get("", response_model=list[CBBResponse])
async def list_cbbs(
    domain: str = None,
    status: str = None,
    q: str = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    query = select(CBB)
    if domain:
        query = query.where(CBB.domain == domain)
    if status:
        query = query.where(CBB.status == status)
    if q:
        query = query.where(CBB.content.ilike(f"%{q}%"))
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/{cbb_id}/deprecate", response_model=CBBResponse)
async def deprecate_cbb(cbb_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CBB).where(CBB.cbb_id == cbb_id))
    cbb = result.scalar_one_or_none()
    if not cbb:
        raise HTTPException(status_code=404, detail="CBB not found")
    cbb.status = "deprecated"
    await db.commit()
    await db.refresh(cbb)
    return cbb