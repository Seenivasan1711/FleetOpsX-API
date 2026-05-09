from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class AiProviderIn(BaseModel):
    provider_name:      str
    model_id:           str
    api_key:            Optional[str] = None
    task_type:          str
    is_active:          bool = True
    is_platform_default: bool = False
    tenant_id:          Optional[UUID] = None  # None = global platform config


class AiProviderUpdate(BaseModel):
    model_id:            Optional[str]  = None
    api_key:             Optional[str]  = None
    is_active:           Optional[bool] = None
    is_platform_default: Optional[bool] = None


class AiProviderOut(BaseModel):
    id:                  UUID
    tenant_id:           Optional[UUID]
    provider_name:       str
    model_id:            str
    task_type:           str
    is_active:           bool
    is_platform_default: bool
    key_set:             bool
    created_at:          datetime
    updated_at:          datetime

    model_config = {"from_attributes": True}


class TenantAiConfigOut(BaseModel):
    platform_defaults: dict  # { "planning": "claude-sonnet-4-6", "chat": "...", "analysis": "..." }
    tenant_overrides:  dict  # per-task overrides for this tenant (or None)
    own_keys_configured: list[str]  # provider names where tenant has their own key
