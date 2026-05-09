"""
Platform-admin endpoints (P4-E1 + P5-E0).

All routes require superadmin role.
"""
from datetime import date, datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_platform_admin
from app.core.db import encrypt_connection_string, mask_connection_string, refresh_route_cache
from app.models.driver import Driver
from app.models.order import Order
from app.models.tenant import Tenant
from app.models.tenant_db_route import TenantDbRoute
from app.models.user import User
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
