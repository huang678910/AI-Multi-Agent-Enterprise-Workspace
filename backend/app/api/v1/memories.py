"""企业记忆 REST API"""

import uuid
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_workspace_role
from app.models.user import User
from app.services.memory_service import MemoryService
from app.schemas.memory import (
    MemoryCreate, MemoryUpdate, MemoryResponse,
    RecallRequest, RecallResult,
    EventCreate, EventUpdate, EventResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workspaces/{workspace_id}/memories", tags=["Enterprise Memory"])


async def _get_svc(workspace_id: str, current_user: User, min_role: str, db: AsyncSession) -> MemoryService:
    await require_workspace_role(workspace_id, current_user, min_role, db)
    return MemoryService(db, workspace_id)


# ─── Memories ──────────────────────────────────────────

@router.get("", response_model=list[MemoryResponse])
async def list_memories(
    workspace_id: uuid.UUID,
    memory_type: str | None = Query(None),
    entity_type: str | None = Query(None),
    min_importance: float | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "member", db)
    return await svc.list_memories(
        memory_type=memory_type, entity_type=entity_type, min_importance=min_importance,
    )


@router.post("", response_model=MemoryResponse, status_code=201)
async def create_memory(
    workspace_id: uuid.UUID,
    data: MemoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    return await svc.create_memory(data)


@router.put("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    workspace_id: uuid.UUID,
    memory_id: uuid.UUID,
    data: MemoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    return await svc.update_memory(str(memory_id), data)


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    workspace_id: uuid.UUID,
    memory_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    await svc.delete_memory(str(memory_id))


@router.post("/recall", response_model=list[RecallResult])
async def recall_memories(
    workspace_id: uuid.UUID,
    data: RecallRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "member", db)
    return await svc.recall(data)


# ─── Events ────────────────────────────────────────────

@router.get("/events", response_model=list[EventResponse])
async def list_events(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "member", db)
    return await svc.list_events()


@router.post("/events", response_model=EventResponse, status_code=201)
async def create_event(
    workspace_id: uuid.UUID,
    data: EventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    return await svc.create_event(data)


@router.delete("/events/{event_id}", status_code=204)
async def delete_event(
    workspace_id: uuid.UUID,
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    await svc.delete_event(str(event_id))
