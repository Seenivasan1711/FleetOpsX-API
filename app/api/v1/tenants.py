"""
Tenant config endpoints — P2-E2

GET  /tenants/config/llm   — read current LLM config for the caller's tenant
PATCH /tenants/config/llm  — upsert llm_provider / llm_api_key / llm_model
"""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db, require_dispatcher
from app.core.config import settings
from app.core.llm_factory import _DEFAULT_MODELS
from app.models.tenant import TenantConfig
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
