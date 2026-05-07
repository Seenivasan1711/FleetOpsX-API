"""Audit log API — P4-E4.

GET /audit/log   — filterable, paginated audit log (admin only)
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.models.audit_log import AuditLogEntry
from app.schemas.audit import AuditLogPage

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/log", response_model=AuditLogPage)
def get_audit_log(
    action:        str | None = Query(None, description="Filter by action string"),
    actor_email:   str | None = Query(None, description="Filter by actor email"),
    resource_type: str | None = Query(None, description="Filter by resource_type"),
    resource_id:   UUID | None = Query(None, description="Filter by resource UUID"),
    since:         datetime | None = Query(None, description="Created after (ISO 8601)"),
    until:         datetime | None = Query(None, description="Created before (ISO 8601)"),
    page:          int = Query(1, ge=1),
    limit:         int = Query(50, ge=1, le=500),
    db:            Session = Depends(get_db),
    current_user=Depends(require_permission("audit:read")),
):
    """Return a paginated, filtered audit log for the authenticated tenant."""
    tid = current_user.tenant_id

    stmt = select(AuditLogEntry).where(AuditLogEntry.tenant_id == tid)

    if action:
        stmt = stmt.where(AuditLogEntry.action == action)
    if actor_email:
        stmt = stmt.where(AuditLogEntry.actor_email == actor_email)
    if resource_type:
        stmt = stmt.where(AuditLogEntry.resource_type == resource_type)
    if resource_id:
        stmt = stmt.where(AuditLogEntry.resource_id == resource_id)
    if since:
        stmt = stmt.where(AuditLogEntry.created_at >= since)
    if until:
        stmt = stmt.where(AuditLogEntry.created_at <= until)

    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one()

    items = db.execute(
        stmt.order_by(AuditLogEntry.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
    ).scalars().all()

    return {"total": total, "items": items}
