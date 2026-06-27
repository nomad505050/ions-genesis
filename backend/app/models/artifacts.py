from sqlalchemy import Column, String, Float, DateTime, Text, JSON, Boolean, Integer
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
    # v0.4 fields
    path_utility = Column(Float, server_default="0.5")
    path_relevance = Column(Float, nullable=True)
    path_rank_score = Column(Float, nullable=True)
    routing_confidence = Column(Float, nullable=True)
    intent = Column(String, server_default="explain")
    cache_hit = Column(Boolean, server_default="false")

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

class CognitiveDomain(Base):
    __tablename__ = "cognitive_domain"

    domain_id = Column(String, primary_key=True)
    label = Column(String, nullable=False)
    description = Column(Text)
    routing_weight = Column(Float, nullable=False, default=1.0)
    decay_tier = Column(String, nullable=False, default="medium")
    nsi_count = Column(Integer, nullable=False, default=0)
    cbb_count = Column(Integer, nullable=False, default=0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())


class RoutingSession(Base):
    __tablename__ = "routing_session"

    session_id = Column(String, primary_key=True)
    query = Column(Text, nullable=False)
    intent = Column(String, nullable=False, default="explain")
    nodes_considered = Column(JSON, nullable=False, default=list)
    domains_considered = Column(JSON, nullable=False, default=list)
    subdomains_considered = Column(JSON, nullable=False, default=list)
    cbbs_discovered = Column(JSON, nullable=False, default=list)
    beam_iterations = Column(Integer)
    conflicts_detected = Column(Integer, default=0)
    selected_path_id = Column(String)
    routing_confidence = Column(Float)
    cache_hit = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ConflictArtifact(Base):
    __tablename__ = "conflict_artifact"

    conflict_id = Column(String, primary_key=True)
    query = Column(Text, nullable=False)
    intent = Column(String)
    path_id_a = Column(String, nullable=False)
    path_id_b = Column(String, nullable=False)
    conclusion_a = Column(Text)
    conclusion_b = Column(Text)
    conflict_type = Column(String)
    resolution = Column(String, default="unresolved")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PathFeedback(Base):
    __tablename__ = "path_feedback"

    feedback_id = Column(String, primary_key=True)
    path_id = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)
    feedback_source = Column(String, default="user")
    query = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PathValidation(Base):
    __tablename__ = "path_validation"

    validation_id = Column(String, primary_key=True)
    path_id = Column(String, nullable=False)
    sample_reason = Column(String)
    coherence_passed = Column(Boolean)
    coherence_break_step = Column(Integer)
    coherence_reason = Column(Text)
    path_optimal = Column(Boolean)
    chosen_score = Column(Float)
    best_alt_score = Column(Float)
    optimality_gap = Column(Float)
    action_taken = Column(String)
    routing_adjustment = Column(JSON)
    validated_at = Column(DateTime(timezone=True), server_default=func.now())