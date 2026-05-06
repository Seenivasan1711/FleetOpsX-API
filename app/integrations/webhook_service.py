"""
Webhook service — P4-E2.

dispatch_event() is called from any endpoint that produces a fleet event
(e.g. driver marks stop DELIVERED). It fans out Celery tasks for each
matching registered webhook.
"""
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.integration import WebhookRegistration

logger = logging.getLogger(__name__)


def dispatch_event(event_type: str, payload: dict, db: Session, tenant_id: str) -> int:
    """Queue webhook delivery for all matching registrations.

    Returns the number of tasks queued.
    """
    from app.workers.tasks import deliver_webhook_task  # local import avoids circular

    webhooks = db.execute(
        select(WebhookRegistration).where(
            WebhookRegistration.tenant_id == tenant_id,
            WebhookRegistration.is_active == True,
        )
    ).scalars().all()

    queued = 0
    for webhook in webhooks:
        event_list = webhook.event_types or []
        if event_type in event_list or "*" in event_list:
            try:
                deliver_webhook_task.apply_async(
                    args=[str(webhook.id), event_type, payload],
                    retry=False,
                )
                queued += 1
            except Exception as exc:
                # Celery broker down — log and continue (don't break the main request)
                logger.error("dispatch_event: failed to queue webhook %s: %s", webhook.id, exc)

    if queued:
        logger.info("dispatch_event: queued %d webhook(s) for %s tenant=%s", queued, event_type, tenant_id)
    return queued
