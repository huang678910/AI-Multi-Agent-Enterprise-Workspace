"""企业记忆 Pydantic Schemas"""

from datetime import datetime, date
from pydantic import BaseModel, Field
import uuid


# ─── Memory ────────────────────────────────────────────

class MemoryCreate(BaseModel):
    memory_type: str = "long_term"
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    importance: float = 5.0
    source_session_id: uuid.UUID | None = None
    source_message_id: uuid.UUID | None = None
    extra_data: dict = {}


class MemoryUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    memory_type: str | None = None
    importance: float | None = None
    extra_data: dict | None = None


class MemoryResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    company_id: uuid.UUID | None = None
    memory_type: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    title: str
    content: str
    importance: float
    access_count: int
    last_recalled_at: datetime | None = None
    source_session_id: uuid.UUID | None = None
    source_message_id: uuid.UUID | None = None
    extra_data: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RecallRequest(BaseModel):
    query: str = Field(..., min_length=1)
    memory_type: str | None = None
    top_k: int = 5


class RecallResult(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    memory_type: str
    importance: float
    similarity: float
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Memory Event ──────────────────────────────────────

class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    event_date: date | None = None
    related_entities: list[dict] = []
    impact: str = "neutral"
    tags: list[str] = []


class EventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    event_date: date | None = None
    related_entities: list[dict] | None = None
    impact: str | None = None
    tags: list[str] | None = None


class EventResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    company_id: uuid.UUID | None = None
    title: str
    description: str | None = None
    event_date: date | None = None
    related_entities: list
    impact: str
    tags: list
    created_at: datetime

    model_config = {"from_attributes": True}
