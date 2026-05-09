"""
Platform-admin endpoints (P4-E1 + P5-E0 + P5-E1).

All routes require superadmin role.
"""
from datetime import date, datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_platform_admin
from app.core.db import encrypt_connection_string, mask_connection_string, refresh_route_cache
from app.models.ai_provider import AiProviderConfig
from app.models.driver import Driver
from app.models.order import Order
from app.models.tenant import Tenant
from app.models.tenant_db_route import TenantDbRoute
from app.models.user import User
from app.schemas.ai_provider import AiProviderIn, AiProviderOut, AiProviderUpdate
from app.schemas.tenant_db_route import TenantDbRouteCreate, TenantDbRouteOut

router = APIRouter(prefix="/admin", tags=["Admin"])


# ---------------------------------------------------------------------------
# P5-E0: Tenant list for superadmin
# ---------------------------------------------------------------------------

class TenantSummary(BaseModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    order_count_today: int
    driver_count: int

    model_config = {"from_attributes": True}


@router.get("/tenants", response_model=List[TenantSummary])
def list_tenants(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    """Return all tenants with today's order count and active driver count."""
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    today_end = datetime.combine(date.today(), datetime.max.time()).replace(tzinfo=timezone.utc)

    tenants = db.execute(select(Tenant).order_by(Tenant.name)).scalars().all()

    result = []
    for t in tenants:
        order_count = db.execute(
            select(func.count(Order.id)).where(
                Order.tenant_id == t.id,
                Order.scheduled_date >= today_start,
                Order.scheduled_date <= today_end,
            )
        ).scalar() or 0

        driver_count = db.execute(
            select(func.count(Driver.id)).where(
                Driver.tenant_id == t.id,
                Driver.is_active == True,
            )
        ).scalar() or 0

        result.append(TenantSummary(
            id=t.id,
            name=t.name,
            slug=t.slug,
            is_active=t.is_active,
            order_count_today=order_count,
            driver_count=driver_count,
        ))

    return result


@router.post("/tenant-db-routes", response_model=TenantDbRouteOut, status_code=201)
def create_tenant_db_route(
    payload: TenantDbRouteCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    """Register a dedicated DB for an enterprise tenant and refresh the routing cache."""
    existing = db.execute(
        select(TenantDbRoute).where(TenantDbRoute.tenant_id == payload.tenant_id)
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=409, detail="Tenant DB route already exists")

    route = TenantDbRoute(
        tenant_id         = payload.tenant_id,
        connection_string = encrypt_connection_string(payload.connection_string),
        region            = payload.region,
        max_pool_size     = payload.max_pool_size,
    )
    db.add(route)
    db.commit()
    db.refresh(route)

    refresh_route_cache(db)

    out = TenantDbRouteOut.model_validate(route)
    out.connection_string = mask_connection_string(route.connection_string)
    return out


@router.get("/tenant-db-routes", response_model=list[TenantDbRouteOut])
def list_tenant_db_routes(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    """List all tenant DB route registrations (connection strings masked)."""
    routes = db.execute(select(TenantDbRoute)).scalars().all()
    result = []
    for r in routes:
        out = TenantDbRouteOut.model_validate(r)
        out.connection_string = mask_connection_string(r.connection_string)
        result.append(out)
    return result


@router.delete("/tenant-db-routes/{tenant_id}", status_code=204)
def delete_tenant_db_route(
    tenant_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    """Remove a dedicated DB route and refresh cache (tenant falls back to shared DB)."""
    from uuid import UUID as _UUID
    route = db.execute(
        select(TenantDbRoute).where(TenantDbRoute.tenant_id == _UUID(tenant_id))
    ).scalar_one_or_none()

    if not route:
        raise HTTPException(status_code=404, detail="Tenant DB route not found")

    db.delete(route)
    db.commit()
    refresh_route_cache(db)


# ---------------------------------------------------------------------------
# P5-E1: AI Provider Management (superadmin CRUD)
# ---------------------------------------------------------------------------

def _provider_out(p: AiProviderConfig) -> AiProviderOut:
    return AiProviderOut(
        id=p.id,
        tenant_id=p.tenant_id,
        provider_name=p.provider_name,
        model_id=p.model_id,
        task_type=p.task_type,
        is_active=p.is_active,
        is_platform_default=p.is_platform_default,
        key_set=bool(p.api_key_enc),
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@router.get("/ai-providers", response_model=List[AiProviderOut])
def list_ai_providers(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    """List all platform-level AI provider configs (superadmin only)."""
    providers = db.execute(
        select(AiProviderConfig)
        .where(AiProviderConfig.tenant_id == None)  # noqa: E711
        .order_by(AiProviderConfig.provider_name, AiProviderConfig.task_type)
    ).scalars().all()
    return [_provider_out(p) for p in providers]


@router.post("/ai-providers", response_model=AiProviderOut, status_code=201)
def create_ai_provider(
    payload: AiProviderIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    """Create a new platform AI provider config. Encrypts the API key."""
    from app.core.db import encrypt_connection_string as _enc

    existing = db.execute(
        select(AiProviderConfig).where(
            AiProviderConfig.tenant_id == None,  # noqa: E711
            AiProviderConfig.provider_name == payload.provider_name,
            AiProviderConfig.task_type == payload.task_type,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Provider config already exists for this task_type")

    if payload.is_platform_default:
        db.execute(
            select(AiProviderConfig).where(
                AiProviderConfig.tenant_id == None,  # noqa: E711
                AiProviderConfig.task_type == payload.task_type,
                AiProviderConfig.is_platform_default == True,  # noqa: E712
            )
        )
        db.query(AiProviderConfig).filter(
            AiProviderConfig.tenant_id == None,
            AiProviderConfig.task_type == payload.task_type,
        ).update({"is_platform_default": False})

    provider = AiProviderConfig(
        tenant_id=None,
        provider_name=payload.provider_name,
        model_id=payload.model_id,
        api_key_enc=_enc(payload.api_key) if payload.api_key else None,
        task_type=payload.task_type,
        is_active=payload.is_active,
        is_platform_default=payload.is_platform_default,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return _provider_out(provider)


@router.put("/ai-providers/{provider_id}", response_model=AiProviderOut)
def update_ai_provider(
    provider_id: str,
    payload: AiProviderUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    """Update an AI provider config (key, model, active status, default flag)."""
    from app.core.db import encrypt_connection_string as _enc

    provider = db.execute(
        select(AiProviderConfig).where(AiProviderConfig.id == UUID(provider_id))
    ).scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="AI provider not found")

    if payload.model_id is not None:
        provider.model_id = payload.model_id
    if payload.api_key is not None:
        provider.api_key_enc = _enc(payload.api_key)
    if payload.is_active is not None:
        provider.is_active = payload.is_active
    if payload.is_platform_default is True:
        db.query(AiProviderConfig).filter(
            AiProviderConfig.tenant_id == None,
            AiProviderConfig.task_type == provider.task_type,
        ).update({"is_platform_default": False})
        provider.is_platform_default = True
    elif payload.is_platform_default is False:
        provider.is_platform_default = False

    db.commit()
    db.refresh(provider)
    return _provider_out(provider)


@router.delete("/ai-providers/{provider_id}", status_code=204)
def delete_ai_provider(
    provider_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    """Delete a platform AI provider config."""
    provider = db.execute(
        select(AiProviderConfig).where(AiProviderConfig.id == UUID(provider_id))
    ).scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="AI provider not found")
    db.delete(provider)
    db.commit()
