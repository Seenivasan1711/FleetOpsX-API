from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.driver import Driver
from app.models.order import Order
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TenantBrief
from app.core.security import hash_password, verify_password, create_access_token


def _build_tenant_list(db: Session):
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    today_end = datetime.combine(date.today(), datetime.max.time()).replace(tzinfo=timezone.utc)
    tenants = db.execute(select(Tenant).where(Tenant.is_active == True).order_by(Tenant.name)).scalars().all()
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
        result.append(TenantBrief(
            id=t.id,
            name=t.name,
            slug=t.slug,
            is_active=t.is_active,
            order_count_today=order_count,
            driver_count=driver_count,
        ))
    return result


def register_user(db: Session, data: RegisterRequest) -> Optional[dict]:
    # Check if email already exists for this tenant
    existing = db.execute(
        select(User).where(
            User.email == data.email,
            User.tenant_id == data.tenant_id,
        )
    ).scalar_one_or_none()

    if existing:
        return None  # caller raises HTTP 409

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
        tenant_id=data.tenant_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role,
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "tenant_id": user.tenant_id,
        "role": user.role,
        "full_name": user.full_name,
    }


def login_user(db: Session, data: LoginRequest) -> Optional[dict]:
    user = db.execute(
        select(User).where(
            User.email == data.email,
            User.is_active == True,
        ).limit(1)
    ).scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        return None  # caller raises HTTP 401

    token = create_access_token({
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "role": user.role,
    })

    response = {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "tenant_id": user.tenant_id,
        "role": user.role,
        "full_name": user.full_name,
        "tenants": None,
    }

    if user.role == "superadmin":
        response["tenants"] = _build_tenant_list(db)

    return response
