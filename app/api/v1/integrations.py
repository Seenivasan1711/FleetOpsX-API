"""
Partner integration endpoints — P4-E2.

POST /integrations/ingest              → normalize + persist partner order
GET  /integrations/tracking-feed       → status + ETA for given order IDs
POST /integrations/webhooks            → register a partner webhook
GET  /integrations/webhooks            → list webhooks for this tenant
DELETE /integrations/webhooks/{id}     → deactivate a webhook
GET  /integrations/logs                → recent integration log entries
POST /integrations/webhooks/{id}/test  → fire a test ping to the webhook URL
"""
from datetime import datetime, date as date_type
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db, require_dispatcher
from app.core.db import encrypt_connection_string, mask_connection_string
from app.models.user import User
from app.models.integration import WebhookRegistration, IntegrationLog
from app.models.order import Order
from app.models.route_plan import RouteStop, Route
from app.schemas.integration import (
    WebhookRegistrationIn, WebhookRegistrationOut,
    IngestRequest, IngestResult, IntegrationLogOut, TrackingFeedItem,
)
from app.integrations.ingest_service import ingest_order
from app.integrations.webhook_service import dispatch_event

router = APIRouter(prefix="/integrations", tags=["Integrations"])


# ─── Ingest ───────────────────────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResult, status_code=202)
def ingest(
    body: IngestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    """Normalize a partner order payload and persist it as an Order."""
    tenant_id = str(current_user.tenant_id)
    return ingest_order(db=db, tenant_id=tenant_id, request=body)


# ─── Tracking feed ────────────────────────────────────────────────────────────

@router.get("/tracking-feed", response_model=list[TrackingFeedItem])
def tracking_feed(
    order_ids: list[str] = Query(..., alias="order_ids[]"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    """Return live status + ETA for the given order IDs."""
    tenant_id = str(current_user.tenant_id)
    result = []

    for oid in order_ids:
        try:
            uid = UUID(oid)
        except ValueError:
            continue

        order = db.execute(
            select(Order).where(Order.id == uid, Order.tenant_id == tenant_id)
        ).scalar_one_or_none()

        if not order:
            continue

        driver_name = None
        eta_minutes = None
        last_ping = None

        # Find assigned driver via RouteStop → Route → Driver
        stop = db.execute(
            select(RouteStop).where(RouteStop.order_id == uid)
        ).scalar_one_or_none()

        if stop:
            route = db.execute(
                select(Route).where(Route.id == stop.route_id)
            ).scalar_one_or_none()
            if route and route.driver:
                driver_name = route.driver.full_name

            # ETA: simple estimate based on sequence (placeholder)
            eta_minutes = stop.sequence * 8  # 8 min per stop

        result.append(TrackingFeedItem(
            order_id=oid,
            status=order.status,
            driver_name=driver_name,
            eta_minutes=eta_minutes,
            last_ping_at=last_ping,
        ))

    return result


# ─── Webhook registry ─────────────────────────────────────────────────────────

@router.post("/webhooks", response_model=WebhookRegistrationOut, status_code=201)
def register_webhook(
    body: WebhookRegistrationIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    """Register a new partner webhook URL for one or more event types."""
    encrypted_secret = None
    if body.secret:
        encrypted_secret = encrypt_connection_string(body.secret)

    webhook = WebhookRegistration(
        tenant_id   = current_user.tenant_id,
        url         = body.url,
        event_types = body.event_types,
        secret      = encrypted_secret,
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return WebhookRegistrationOut.model_validate(webhook)


@router.get("/webhooks", response_model=list[WebhookRegistrationOut])
def list_webhooks(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    rows = db.execute(
        select(WebhookRegistration).where(
            WebhookRegistration.tenant_id == current_user.tenant_id
        )
    ).scalars().all()
    return [WebhookRegistrationOut.model_validate(r) for r in rows]


@router.delete("/webhooks/{webhook_id}", status_code=204)
def delete_webhook(
    webhook_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    webhook = db.execute(
        select(WebhookRegistration).where(
            WebhookRegistration.id == webhook_id,
            WebhookRegistration.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    webhook.is_active = False
    db.commit()


@router.post("/webhooks/{webhook_id}/test", status_code=202)
def test_webhook(
    webhook_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    """Fire a test ping to the webhook URL."""
    webhook = db.execute(
        select(WebhookRegistration).where(
            WebhookRegistration.id == webhook_id,
            WebhookRegistration.tenant_id == current_user.tenant_id,
            WebhookRegistration.is_active == True,
        )
    ).scalar_one_or_none()

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found or inactive")

    queued = dispatch_event(
        event_type="webhook.test",
        payload={"message": "FleetOpsX webhook test ping", "webhook_id": str(webhook_id)},
        db=db,
        tenant_id=str(current_user.tenant_id),
    )
    return {"queued": queued > 0, "message": "Test event queued" if queued else "No Celery worker — test not queued"}


# ─── Integration logs ─────────────────────────────────────────────────────────

@router.get("/logs", response_model=list[IntegrationLogOut])
def integration_logs(
    since: Optional[str] = Query(None, description="ISO date e.g. 2026-05-01"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    q = select(IntegrationLog).where(
        IntegrationLog.tenant_id == current_user.tenant_id
    ).order_by(IntegrationLog.created_at.desc()).limit(limit)

    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            q = q.where(IntegrationLog.created_at >= since_dt)
        except ValueError:
            pass

    rows = db.execute(q).scalars().all()
    return [IntegrationLogOut.model_validate(r) for r in rows]
