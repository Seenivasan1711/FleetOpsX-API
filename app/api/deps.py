import logging
from typing import Generator, Optional
from uuid import UUID
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError
from app.core.db import get_db, get_db_for_tenant
from app.core.security import decode_token
from app.models.user import User
from sqlalchemy import select

# Sentinel — used by get_effective_tenant_id default
_UNSET = object()

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> User:
    """Extracts user from JWT Bearer token."""
    if credentials:
        try:
            payload = decode_token(credentials.credentials)
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token payload")

            user = db.execute(
                select(User).where(User.id == UUID(user_id), User.is_active == True)
            ).scalar_one_or_none()

            if not user:
                raise HTTPException(status_code=401, detail="User not found or inactive")

            return user
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_tenant_id(
    current_user: User = Depends(get_current_user),
) -> str:
    """Returns tenant_id string from the authenticated user's token."""
    return str(current_user.tenant_id)


def require_dispatcher(current_user: User = Depends(get_current_user)) -> User:
    """Only allows dispatcher or admin roles."""
    if current_user.role not in ("dispatcher", "admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Dispatcher role required")
    return current_user


def require_driver(current_user: User = Depends(get_current_user)) -> User:
    """Only allows driver role."""
    if current_user.role != "driver":
        raise HTTPException(status_code=403, detail="Driver role required")
    return current_user


def require_platform_admin(current_user: User = Depends(get_current_user)) -> User:
    """Allows admin or superadmin role — platform-level operations."""
    if current_user.role not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_tenant_admin(current_user: User = Depends(get_current_user)) -> User:
    """Allows tenant admin or superadmin — tenant user management (P5-E8)."""
    if current_user.role not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Tenant admin role required")
    return current_user


def require_permission(permission: str):
    """Factory dep: raises 403 if the authenticated user lacks the given permission."""
    def _check(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        from app.services.rbac_service import check_permission
        if not check_permission(current_user, permission, db):
            raise HTTPException(status_code=403, detail=f"Permission required: {permission}")
        return current_user
    return _check


def get_effective_tenant_id(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_acting_tenant_id: Optional[str] = Header(default=None),
) -> UUID:
    """Returns the effective tenant_id for the current request.

    For superadmins: uses X-Acting-Tenant-Id header (validated against tenants table).
    For all other roles: returns user's own tenant_id.
    """
    if current_user.role == "superadmin" and x_acting_tenant_id:
        from app.models.tenant import Tenant
        try:
            acting_id = UUID(x_acting_tenant_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid X-Acting-Tenant-Id format")

        tenant = db.execute(
            select(Tenant).where(Tenant.id == acting_id, Tenant.is_active == True)
        ).scalar_one_or_none()

        if not tenant:
            raise HTTPException(status_code=404, detail="Acting tenant not found or inactive")

        return acting_id

    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="No tenant associated with this account")

    return current_user.tenant_id


def get_tenant_db(current_user: User = Depends(get_current_user)) -> Generator[Session, None, None]:
    """Yields a DB session routed to the authenticated tenant's database (P4-E1).

    Falls back to the shared DB for tenants without a dedicated route.
    Auth always uses the shared DB via get_current_user → no circular dependency.
    """
    db = get_db_for_tenant(str(current_user.tenant_id))
    try:
        yield db
    finally:
        db.close()
