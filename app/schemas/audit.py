"""Schemas for Governance & Audit (P4-E4)."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:            UUID
    created_at:    datetime
    actor_email:   str
    actor_role:    str
    action:        str
    resource_type: str
    resource_id:   UUID | None = None
    before_state:  Any | None = None
    after_state:   Any | None = None
    ip_address:    str | None = None
    user_agent:    str | None = None
    ai_context:    Any | None = None


class AuditLogPage(BaseModel):
    total: int
    items: list[AuditLogEntryOut]


class DataExportRequest(BaseModel):
    """Body is empty — export always covers the authenticated tenant's full data."""
    pass


class DataExportStatus(BaseModel):
    task_id:      str
    status:       str          # PENDING | SUCCESS | FAILURE
    download_url: str | None = None
    error:        str | None = None


class RetentionConfigIn(BaseModel):
    retention_days: int        # e.g. 365


class RetentionConfigOut(BaseModel):
    retention_days: int
    updated_at:    datetime | None = None


class RbacRoleIn(BaseModel):
    name:        str
    permissions: list[str]


class RbacRoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:          UUID
    name:        str
    permissions: list[str]
    is_system:   bool
    tenant_id:   UUID
