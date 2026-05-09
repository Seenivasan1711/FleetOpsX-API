"""
Tenant config endpoints — P2-E2 + P5-E1

GET  /tenants/config/llm        — read current LLM config for the caller's tenant
PATCH /tenants/config/llm       — upsert llm_provider / llm_api_key / llm_model
GET  /tenants/settings/ai-config — P5-E1 tenant AI config view
PATCH /tenants/settings/ai-config — P5-E1 tenant AI override update
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db, get_effective_tenant_id, require_dispatcher
from app.core.config import settings
from app.core.llm_factory import _DEFAULT_MODELS
from app.models.ai_provider import AiProviderConfig
from app.models.tenant import TenantConfig
from app.models.user import User
from app.schemas.ai_provider import TenantAiConfigOut
from app.schemas.tenant import LLMConfigOut, LLMConfigUpdate

router = APIRouter(prefix="/tenants", tags=["Tenants"])

_LLM_KEYS = ("llm_provider", "llm_api_key", "llm_model")


def _get_kv(db: Session, tenant_id: UUID) -> dict:
    rows = db.execute(
        select(TenantConfig).where(
            TenantConfig.tenant_id == tenant_id,
            TenantConfig.config_key.in_(_LLM_KEYS),
        )
    ).scalars().all()
    return {r.config_key: r.config_value for r in rows}


def _upsert(db: Session, tenant_id: UUID, key: str, value: str) -> None:
    row = db.execute(
        select(TenantConfig).where(
            TenantConfig.tenant_id == tenant_id,
            TenantConfig.config_key == key,
        )
    ).scalar_one_or_none()
    if row:
        row.config_value = value
    else:
        db.add(TenantConfig(tenant_id=tenant_id, config_key=key, config_value=value))


@router.get("/config/llm", response_model=LLMConfigOut)
def get_llm_config(
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Return the LLM configuration for the caller's tenant."""
    tid = UUID(str(current_user.tenant_id))
    kv = _get_kv(db, tid)

    provider = (kv.get("llm_provider") or settings.LLM_PROVIDER).lower()
    model = kv.get("llm_model") or _DEFAULT_MODELS.get(provider, "unknown")
    api_key_set = bool(kv.get("llm_api_key"))

    return LLMConfigOut(provider=provider, model=model, api_key_set=api_key_set)


@router.patch("/config/llm", response_model=LLMConfigOut)
def update_llm_config(
    body: LLMConfigUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Upsert LLM config keys for the caller's tenant."""
    tid = UUID(str(current_user.tenant_id))

    if body.provider is not None:
        _upsert(db, tid, "llm_provider", body.provider)
    if body.api_key is not None:
        _upsert(db, tid, "llm_api_key", body.api_key)
    if body.model is not None:
        _upsert(db, tid, "llm_model", body.model)

    db.commit()

    # Re-read to return current state
    kv = _get_kv(db, tid)
    provider = (kv.get("llm_provider") or settings.LLM_PROVIDER).lower()
    model = kv.get("llm_model") or _DEFAULT_MODELS.get(provider, "unknown")
    api_key_set = bool(kv.get("llm_api_key"))

    return LLMConfigOut(provider=provider, model=model, api_key_set=api_key_set)


# ---------------------------------------------------------------------------
# P5-E1: Tenant AI config view
# ---------------------------------------------------------------------------

@router.get("/settings/ai-config", response_model=TenantAiConfigOut)
def get_tenant_ai_config(
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_effective_tenant_id),
    current_user: User = Depends(require_dispatcher),
):
    """Return platform defaults + tenant overrides for AI model selection."""
    task_types = ["planning", "chat", "analysis"]

    platform_defaults: dict = {}
    for task in task_types:
        default = db.execute(
            select(AiProviderConfig).where(
                AiProviderConfig.tenant_id == None,  # noqa: E711
                AiProviderConfig.task_type == task,
                AiProviderConfig.is_platform_default == True,  # noqa: E712
            )
        ).scalar_one_or_none()
        platform_defaults[task] = default.model_id if default else None

    tenant_overrides: dict = {}
    own_keys: list = []
    for task in task_types:
        override = db.execute(
            select(AiProviderConfig).where(
                AiProviderConfig.tenant_id == tenant_id,
                AiProviderConfig.task_type == task,
                AiProviderConfig.is_active == True,  # noqa: E712
            )
        ).scalar_one_or_none()
        if override:
            tenant_overrides[task] = override.model_id
            if override.api_key_enc and override.provider_name not in own_keys:
                own_keys.append(override.provider_name)
        else:
            tenant_overrides[task] = None

    return TenantAiConfigOut(
        platform_defaults=platform_defaults,
        tenant_overrides=tenant_overrides,
        own_keys_configured=own_keys,
    )


from pydantic import BaseModel as _BaseModel


class TenantAiConfigUpdate(_BaseModel):
    task_type:     str
    model_id:      Optional[str] = None
    api_key:       Optional[str] = None
    provider_name: Optional[str] = None


@router.patch("/settings/ai-config")
def update_tenant_ai_config(
    body: TenantAiConfigUpdate,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_effective_tenant_id),
    current_user: User = Depends(require_dispatcher),
):
    """Upsert a tenant-specific AI provider config for a given task_type."""
    from app.core.db import encrypt_connection_string as _enc
    from fastapi import HTTPException as _HTTPException

    existing = db.execute(
        select(AiProviderConfig).where(
            AiProviderConfig.tenant_id == tenant_id,
            AiProviderConfig.task_type == body.task_type,
        )
    ).scalar_one_or_none()

    if existing:
        if body.model_id:
            existing.model_id = body.model_id
        if body.api_key:
            existing.api_key_enc = _enc(body.api_key)
    else:
        if not body.provider_name or not body.model_id:
            raise _HTTPException(status_code=400, detail="provider_name and model_id required for new config")
        new_config = AiProviderConfig(
            tenant_id=tenant_id,
            provider_name=body.provider_name,
            model_id=body.model_id,
            api_key_enc=_enc(body.api_key) if body.api_key else None,
            task_type=body.task_type,
            is_active=True,
            is_platform_default=False,
        )
        db.add(new_config)

    db.commit()
    return {"status": "updated"}
