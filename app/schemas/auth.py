from pydantic import BaseModel
from uuid import UUID


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "dispatcher"  # dispatcher | driver
    tenant_id: UUID           # which tenant to register under


class LoginRequest(BaseModel):
    email: str
    password: str
    tenant_id: UUID           # required — one email can exist in multiple tenants


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    tenant_id: UUID
    role: str
    full_name: str
