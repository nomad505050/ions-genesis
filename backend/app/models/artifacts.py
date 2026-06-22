from sqlalchemy import Column, String, Float, DateTime, Text, JSON, Boolean
from sqlalchemy.sql import func
from app.core.database import Base

class CBB(Base):
    __tablename__ = "cbb"

    cbb_id = Column(String, primary_key=True)
    type = Column(String, nullable=False, default="claim")
    domain = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=False, default=list)
    confidence = Column(Float, nullable=False)
    assumptions = Column(JSON, nullable=False, default=list)
    scope = Column(JSON, nullable=False, default=list)
    tags = Column(JSON, nullable=False, default=list)
    creator = Column(String, nullable=False)
    status = Column(String, nullable=False, default="candidate")
    version = Column(String, nullable=False, default="1.0")
    hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Relationship(Base):
    __tablename__ = "relationship"

    relationship_id = Column(String, primary_key=True)
    source_cbb_id = Column(String, nullable=False)
    target_cbb_id = Column(String, nullable=False)
    relationship_type = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    rationale = Column(Text)
    creator = Column(String, nullable=False)
    status = Column(String, nullable=False, default="candidate")
    hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ReasoningPath(Base):
    __tablename__ = "reasoning_path"

    path_id = Column(String, primary_key=True)
    query = Column(Text, nullable=False)
    cbb_sequence = Column(JSON, nullable=False)
    relationship_sequence = Column(JSON, nullable=False)
    path_confidence = Column(Float, nullable=False)
    evidence_score = Column(Float, nullable=False)
    answer = Column(Text, nullable=False)
    path_explanation = Column(Text, nullable=False)
    model_used = Column(String)
    hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LineageEvent(Base):
    __tablename__ = "lineage_event"

    event_id = Column(String, primary_key=True)
    artifact_type = Column(String, nullable=False)
    artifact_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    parent_artifact_ids = Column(JSON, nullable=False, default=list)
    child_artifact_ids = Column(JSON, nullable=False, default=list)
    actor = Column(String, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class NodeRegistry(Base):
    __tablename__ = "node_registry"

    node_id = Column(String, primary_key=True)
    protocol_version = Column(String, nullable=False, default="ions-genesis-0.1")
    public_api_base = Column(String, nullable=False)
    manifest_url = Column(String, nullable=False)
    domains = Column(JSON, nullable=False, default=list)  # list of domains this node covers
    capabilities = Column(JSON, nullable=False, default=list)
    status = Column(String, nullable=False, default="active")  # active, unreachable, deprecated
    open_contributions = Column(Boolean, nullable=False, default=True)
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    description = Column(Text, nullable=True)
