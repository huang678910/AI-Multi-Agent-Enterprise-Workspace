"""Celery App - async task queue backed by Redis"""

from celery import Celery
from app.config import get_settings

settings = get_settings()

celery = Celery(
    "ai_workspace",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.document_tasks",
        "app.tasks.report_tasks",
    ],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_soft_time_limit=300,   # 5 min soft limit
    task_time_limit=600,        # 10 min hard limit
)
