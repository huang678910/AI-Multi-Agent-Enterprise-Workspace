"""聚合所有 v1 路由"""
from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.workspaces import router as workspace_router
from app.api.v1.documents import router as document_router
from app.api.v1.chat import router as chat_router
from app.api.v1.search import router as search_router
from app.api.v1.ws import router as ws_router
from app.api.v1.members import router as members_router
from app.api.v1.users import router as users_router
from app.api.v1.reports import router as reports_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.company import router as company_router
from app.api.v1.memories import router as memories_router
from app.api.v1.graph import router as graph_router
from app.api.v1.knowledge import router as knowledge_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(workspace_router)
api_router.include_router(document_router)
api_router.include_router(chat_router)
api_router.include_router(search_router)
api_router.include_router(ws_router)
api_router.include_router(members_router)
api_router.include_router(users_router)
api_router.include_router(reports_router)
api_router.include_router(tasks_router)
api_router.include_router(company_router)
api_router.include_router(memories_router)
api_router.include_router(graph_router)
api_router.include_router(knowledge_router)
