from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "dispatcher"  # dispatcher | driver
    tenant_id: UUID           # which tenant to register under


class LoginRequest(BaseModel):
    email: str
    password: str


class TenantBrief(BaseModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    order_count_today: int
    driver_count: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    tenant_id: Optional[UUID] = None
    role: str
    full_name: str
    tenants: Optional[List[TenantBrief]] = None
