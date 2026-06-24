import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.core.database import get_db
from app.models.artifacts import CBB
from app.models.schemas import CBBCreate, CBBResponse
from app.services.hashing import canonical_hash
from app.services.embedding import ensure_domain_registered

router = APIRouter(prefix="/cbb", tags=["cbbs"])

@router.post("", response_model=CBBResponse)
async def create_cbb(payload: CBBCreate, db: AsyncSession = Depends(get_db)):
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
    # Auto-embed domain for NSI clustering
    if payload.domain:
        try:
            await ensure_domain_registered(payload.domain, db)
        except Exception:
            pass  # never block CBB creation on embedding failure
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