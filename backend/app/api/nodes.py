"""
IONS Node Registry — federation endpoints.
Handles node registration, discovery, and health checking.
"""
import uuid
import httpx
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db
from app.models.artifacts import NodeRegistry

router = APIRouter(prefix="/nodes", tags=["nodes"])


class NodeRegisterRequest(BaseModel):
    node_id: str
    public_api_base: str
    description: Optional[str] = None


class NodeResponse(BaseModel):
    node_id: str
    public_api_base: str
    manifest_url: str
    domains: List[str]
    capabilities: List[str]
    status: str
    open_contributions: bool
    last_seen: Optional[datetime]
    registered_at: Optional[datetime]
    description: Optional[str]


async def fetch_manifest(public_api_base: str) -> dict:
    """Fetch and validate a node's manifest."""
    url = f"{public_api_base.rstrip('/')}/.well-known/ions-node.json"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


@router.get("", response_model=List[NodeResponse])
async def list_nodes(
    status: Optional[str] = "active",
    db: AsyncSession = Depends(get_db)
):
    """List all registered nodes."""
    query = select(NodeRegistry)
    if status:
        query = query.where(NodeRegistry.status == status)
    result = await db.execute(query)
    nodes = result.scalars().all()
    return [
        NodeResponse(
            node_id=n.node_id,
            public_api_base=n.public_api_base,
            manifest_url=n.manifest_url,
            domains=n.domains or [],
            capabilities=n.capabilities or [],
            status=n.status,
            open_contributions=n.open_contributions,
            last_seen=n.last_seen,
            registered_at=n.registered_at,
            description=n.description,
        )
        for n in nodes
    ]


@router.post("/register", response_model=NodeResponse)
async def register_node(
    payload: NodeRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new node by fetching and validating its manifest.
    The node must be running and accessible.
    """
    # Fetch the manifest to validate the node is live
    try:
        manifest = await fetch_manifest(payload.public_api_base)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not fetch node manifest from {payload.public_api_base}: {str(e)}"
        )

    # Validate manifest has required fields
    if "node_id" not in manifest or "protocol_version" not in manifest:
        raise HTTPException(
            status_code=400,
            detail="Invalid node manifest — missing required fields"
        )

    node_id = manifest.get("node_id", payload.node_id)
    manifest_url = f"{payload.public_api_base.rstrip('/')}/.well-known/ions-node.json"

    # Check if node already exists
    existing = await db.get(NodeRegistry, node_id)
    if existing:
        # Update existing node
        existing.public_api_base = payload.public_api_base
        existing.manifest_url = manifest_url
        existing.domains = manifest.get("domains", [])
        existing.capabilities = manifest.get("capabilities", [])
        existing.status = "active"
        existing.open_contributions = manifest.get("open_contributions", True)
        existing.last_seen = datetime.now(timezone.utc)
        existing.description = payload.description or manifest.get("description")
        await db.commit()
        node = existing
    else:
        node = NodeRegistry(
            node_id=node_id,
            protocol_version=manifest.get("protocol_version", "ions-genesis-0.1"),
            public_api_base=payload.public_api_base,
            manifest_url=manifest_url,
            domains=manifest.get("domains", []),
            capabilities=manifest.get("capabilities", []),
            status="active",
            open_contributions=manifest.get("open_contributions", True),
            description=payload.description or manifest.get("description"),
        )
        db.add(node)
        await db.commit()

    return NodeResponse(
        node_id=node.node_id,
        public_api_base=node.public_api_base,
        manifest_url=node.manifest_url,
        domains=node.domains or [],
        capabilities=node.capabilities or [],
        status=node.status,
        open_contributions=node.open_contributions,
        last_seen=node.last_seen,
        registered_at=node.registered_at,
        description=node.description,
    )


@router.post("/{node_id}/ping")
async def ping_node(node_id: str, db: AsyncSession = Depends(get_db)):
    """
    Health check a registered node and update its status and domain list.
    """
    node = await db.get(NodeRegistry, node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

    try:
        manifest = await fetch_manifest(node.public_api_base)
        node.status = "active"
        node.domains = manifest.get("domains", node.domains)
        node.capabilities = manifest.get("capabilities", node.capabilities)
        node.last_seen = datetime.now(timezone.utc)
        await db.commit()
        return {"node_id": node_id, "status": "active", "last_seen": node.last_seen}
    except Exception as e:
        node.status = "unreachable"
        await db.commit()
        return {"node_id": node_id, "status": "unreachable", "error": str(e)}


@router.delete("/{node_id}")
async def deregister_node(node_id: str, db: AsyncSession = Depends(get_db)):
    """Remove a node from the registry."""
    node = await db.get(NodeRegistry, node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    await db.delete(node)
    await db.commit()
    return {"node_id": node_id, "status": "deregistered"}
