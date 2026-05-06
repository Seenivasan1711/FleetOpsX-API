"""
Ingest service — P4-E2.

Selects the right adapter by source_system, checks idempotency, creates the Order.
"""
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.integrations.base_adapter import BaseAdapter
from app.integrations.adapters.sap_adapter import SAPAdapter
from app.integrations.adapters.shopify_adapter import ShopifyAdapter
from app.integrations.adapters.generic_adapter import GenericAdapter
from app.models.integration import IntegrationLog
from app.schemas.integration import IngestRequest, IngestResult
from app.schemas.order import OrderCreate
from app.services.order_service import create_order

logger = logging.getLogger(__name__)

_ADAPTERS: dict[str, BaseAdapter] = {
    "SAP":     SAPAdapter(),
    "Shopify": ShopifyAdapter(),
    "generic": GenericAdapter(),
}


def ingest_order(db: Session, tenant_id: str, request: IngestRequest) -> IngestResult:
    """Normalize and persist a partner order, honouring idempotency."""
    existing = db.execute(
        select(IntegrationLog).where(
            IntegrationLog.tenant_id == tenant_id,
            IntegrationLog.partner_order_id == request.partner_order_id,
        )
    ).scalar_one_or_none()

    if existing:
        return IngestResult(
            order_id=str(existing.order_id) if existing.order_id else None,
            status="skipped",
            idempotent=True,
        )

    adapter = _ADAPTERS.get(request.source_system, _ADAPTERS["generic"])
    log = IntegrationLog(
        tenant_id=tenant_id,
        partner_order_id=request.partner_order_id,
        source_system=request.source_system,
        raw_payload=request.payload,
    )

    try:
        order_create: OrderCreate = adapter.transform(request.payload)
        order = create_order(db=db, tenant_id=tenant_id, data=order_create)
        log.normalized = True
        log.order_id = order.id
        db.add(log)
        db.commit()
        logger.info("ingest: %s/%s → order %s", request.source_system, request.partner_order_id, order.id)
        return IngestResult(order_id=str(order.id), status="created", idempotent=False)

    except Exception as exc:
        log.normalized = False
        log.error_message = str(exc)
        db.add(log)
        db.commit()
        logger.error("ingest: %s/%s failed: %s", request.source_system, request.partner_order_id, exc)
        return IngestResult(status="error", idempotent=False)
