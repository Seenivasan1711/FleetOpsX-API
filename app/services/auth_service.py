from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest
from app.core.security import hash_password, verify_password, create_access_token


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
            User.tenant_id == data.tenant_id,
            User.is_active == True,
        )
    ).scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        return None  # caller raises HTTP 401

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
