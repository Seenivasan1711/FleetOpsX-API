"""
P5-E8: Tenant user management.

GET    /users           — list all users in tenant
POST   /users/invite    — create user with temp password
PUT    /users/{user_id} — update role / full_name / is_active
DELETE /users/{user_id} — deactivate (soft-delete)
"""
import secrets
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_tenant_admin
from app.core.security import hash_password
from app.models.user import User

router = APIRouter(prefix="/users", tags=["User Management"])

ALLOWED_ROLES = {"dispatcher", "driver", "admin", "readonly", "packaging_team"}


class UserOut(BaseModel):
    id:        UUID
    email:     str
    full_name: Optional[str]
    role:      str
    is_active: bool

    class Config:
        from_attributes = True


class InviteIn(BaseModel):
    email:     EmailStr
    full_name: str
    role:      str = "dispatcher"


class InviteOut(BaseModel):
    user:          UserOut
    temp_password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role:      Optional[str] = None
    is_active: Optional[bool] = None


@router.get("", response_model=List[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin),
):
    """List all users in the current tenant."""
    users = db.execute(
        select(User)
        .where(User.tenant_id == current_user.tenant_id)
        .order_by(User.full_name)
    ).scalars().all()
    return users


@router.post("/invite", response_model=InviteOut, status_code=201)
def invite_user(
    body: InviteIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin),
):
    """Create a new user in the tenant. Returns a temporary password to share."""
    if body.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {', '.join(sorted(ALLOWED_ROLES))}")

    existing = db.execute(
        select(User).where(User.email == body.email, User.tenant_id == current_user.tenant_id)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="A user with this email already exists in the tenant")

    temp_pw = secrets.token_urlsafe(12)
    user = User(
        id=uuid4(),
        tenant_id=current_user.tenant_id,
        email=body.email,
        full_name=body.full_name,
        role=body.role,
        hashed_password=hash_password(temp_pw),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return InviteOut(user=UserOut.model_validate(user), temp_password=temp_pw)


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: UUID,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin),
):
    """Update a user's role, name, or active status."""
    user = db.execute(
        select(User).where(User.id == user_id, User.tenant_id == current_user.tenant_id)
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.role and body.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {', '.join(sorted(ALLOWED_ROLES))}")

    if body.role      is not None: user.role      = body.role
    if body.full_name is not None: user.full_name = body.full_name
    if body.is_active is not None: user.is_active = body.is_active

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
def deactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin),
):
    """Deactivate a user (soft-delete — they cannot log in)."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    user = db.execute(
        select(User).where(User.id == user_id, User.tenant_id == current_user.tenant_id)
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    db.commit()
