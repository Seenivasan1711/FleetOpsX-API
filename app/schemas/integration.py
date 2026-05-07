from pydantic import BaseModel, UUID4, HttpUrl
from typing import Optional, Any
from datetime import datetime


# ─── Webhook schemas ──────────────────────────────────────────────────────────

class WebhookRegistrationIn(BaseModel):
    url:         str
    event_types: list[str]   # ["order.delivered", "order.delayed", "route.updated"]
    secret:      Optional[str] = None


class WebhookRegistrationOut(BaseModel):
    id:          UUID4
    tenant_id:   UUID4
    url:         str
    event_types: list[str]
    is_active:   bool
    last_error:  Optional[str] = None
    created_at:  Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Ingest schemas ───────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    source_system:    str            # "SAP" | "Shopify" | "generic"
    partner_order_id: str            # idempotency key
    payload:          dict[str, Any] # raw partner data


class IngestResult(BaseModel):
    order_id:   Optional[str] = None
    status:     str           # "created" | "skipped" | "error"
    idempotent: bool = False  # True if already existed


# ─── Integration log schemas ──────────────────────────────────────────────────

class IntegrationLogOut(BaseModel):
    id:               UUID4
    partner_order_id: str
    source_system:    str
    normalized:       bool
    order_id:         Optional[UUID4] = None
    error_message:    Optional[str] = None
    created_at:       Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Tracking feed schemas ────────────────────────────────────────────────────

class TrackingFeedItem(BaseModel):
    order_id:     str
    status:       str
    driver_name:  Optional[str] = None
    eta_minutes:  Optional[int] = None
    last_ping_at: Optional[str] = None
