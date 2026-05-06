"""Audit service — append-only log_action helper (P4-E4).

All writes go through log_action(). Nothing else touches audit_log_entries.
Failures are swallowed with a warning so a logging bug never breaks the
primary action that triggered it.
"""
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLogEntry
from app.models.user import User

logger = logging.getLogger(__name__)


def log_action(
    *,
    db: Session,
    actor: User,
    action: str,
    resource_type: str,
    resource_id: UUID | str | None = None,
    before: Any | None = None,
    after: Any | None = None,
    ai_context: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLogEntry | None:
    """Insert a single immutable AuditLogEntry.

    Never raises — any exception is caught and logged so audit failures cannot
    break the caller's primary operation.
    """
    try:
        rid = UUID(str(resource_id)) if resource_id else None
        entry = AuditLogEntry(
            tenant_id=actor.tenant_id,
            actor_email=actor.email or str(actor.id),
            actor_role=actor.role,
            action=action,
            resource_type=resource_type,
            resource_id=rid,
            before_state=before,
            after_state=after,
            ai_context=ai_context,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(entry)
        db.flush()
        return entry
    except Exception as exc:
        logger.warning("audit log_action failed (action=%s): %s", action, exc, exc_info=True)
        return None
