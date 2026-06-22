from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional, List
from datetime import datetime

class EvidenceRef(BaseModel):
    source_type: str
    source_id: str
    uri: Optional[str] = None
    note: Optional[str] = None
    visibility: Literal["public", "private", "internal"] = "internal"

class CBBCreate(BaseModel):
    type: Literal["claim"] = "claim"
    domain: str = Field(min_length=2, max_length=120)
    content: str = Field(min_length=10, max_length=800)
    evidence: List[EvidenceRef] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    assumptions: List[str] = Field(default_factory=list)
    scope: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    status: Literal["candidate", "approved", "published", "deprecated", "rejected"] = "candidate"

    @field_validator("content")
    @classmethod
    def no_empty_claim(cls, value: str):
        if value.strip() == "":
            raise ValueError("content cannot be empty")
        return value.strip()

class CBBResponse(CBBCreate):
    cbb_id: str
    creator: str
    version: str
    hash: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class RelationshipCreate(BaseModel):
    source_cbb_id: str
    target_cbb_id: str
    relationship_type: Literal[
        "supports", "contradicts", "depends_on", "causes",
        "correlates_with", "extends", "refines", "references"
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: Optional[str] = None
    status: Literal["candidate", "approved", "published", "deprecated", "rejected"] = "candidate"

class RelationshipResponse(RelationshipCreate):
    relationship_id: str
    creator: str
    hash: str
    created_at: datetime

    class Config:
        from_attributes = True