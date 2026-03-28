import logging
from typing import Optional
from uuid import UUID
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError
from app.core.db import get_db
from app.core.security import decode_token
from app.models.user import User
from sqlalchemy import select

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
