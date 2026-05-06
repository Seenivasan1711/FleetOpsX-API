"""
Celery application — P4-E2.

Broker and result backend both use Redis (already required for GPS tracking cache).
Worker is started separately: `celery -A app.workers.celery_app worker --loglevel=info`
"""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "fleetopsx",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)
