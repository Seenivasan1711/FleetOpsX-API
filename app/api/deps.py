import logging
from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from app.core.db import get_db

logger = logging.getLogger(__name__)


def get_tenant_id(
    x_tenant_id: Optional[str] = Header(default=None),
) -> Optional[str]:
    """Returns tenant_id or None. Use where tenant is optional."""
    return x_tenant_id


def require_tenant_id(
    tenant_id: Optional[str] = Depends(get_tenant_id),
) -> str:
    """Raises HTTP 400 if X-Tenant-ID header is missing. Use on all domain endpoints."""
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header is required",
        )
    return tenant_id
