"""Async task status API"""

from fastapi import APIRouter
from app.celery_app import celery

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/{task_id}")
async def get_task_status(task_id: str):
    """Get Celery task status and result"""
    result = celery.AsyncResult(task_id)
    response = {
        "task_id": task_id,
        "status": result.state,
        "ready": result.ready(),
    }
    if result.ready():
        if result.successful():
            response["result"] = result.result
        else:
            response["error"] = str(result.info) if result.info else "Unknown error"
    else:
        response["info"] = str(result.info) if result.info else None
    return response
