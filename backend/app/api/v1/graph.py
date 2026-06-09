"""知识图谱 REST API — /api/v1/workspaces/{workspace_id}/graph/..."""

import uuid
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_workspace_role
from app.models.user import User
from app.services.graph_service import GraphService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workspaces/{workspace_id}/graph", tags=["Knowledge Graph"])


async def _get_svc(workspace_id: str, current_user: User, min_role: str, db: AsyncSession) -> GraphService:
    await require_workspace_role(workspace_id, current_user, min_role, db)
    return GraphService(workspace_id)


@router.post("/query")
async def graph_query(
    workspace_id: uuid.UUID,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute a read-only Cypher query on the knowledge graph"""
    await _get_svc(str(workspace_id), current_user, "member", db)
    cypher = body.get("query", body.get("cypher", ""))
    params = body.get("params", {})
    if not cypher:
        return {"error": "Query (Cypher) is required"}
    svc = GraphService(str(workspace_id))
    results = svc.query(cypher, params)
    return {"results": results, "count": len(results)}


@router.post("/search")
async def graph_search(
    workspace_id: uuid.UUID,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search entities and their relationships (GraphRAG)"""
    await _get_svc(str(workspace_id), current_user, "member", db)
    query_text = body.get("query", "")
    top_k = body.get("top_k", 5)
    if not query_text:
        return {"results": [], "count": 0}

    svc = GraphService(str(workspace_id))
    results = svc.search(query_text, top_k)
    return {"results": results, "count": len(results)}


@router.get("/stats")
async def graph_stats(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get knowledge graph statistics"""
    await _get_svc(str(workspace_id), current_user, "member", db)
    svc = GraphService(str(workspace_id))
    return svc.get_stats()


@router.post("/sync")
async def graph_sync(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full sync: export all Layer 1 company data to Neo4j knowledge graph"""
    await _get_svc(str(workspace_id), current_user, "admin", db)
    svc = GraphService(str(workspace_id))
    stats = await svc.full_sync_from_db(db)
    return {"status": "completed", "stats": stats}
