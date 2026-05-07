from pydantic import BaseModel, UUID4
from typing import Optional


class TenantDbRouteCreate(BaseModel):
    tenant_id:         UUID4
    connection_string: str
    region:            Optional[str] = None
    max_pool_size:     int = 10


class TenantDbRouteOut(BaseModel):
    id:                UUID4
    tenant_id:         UUID4
    connection_string: str       # masked in serializer
    region:            Optional[str]
    is_active:         bool
    max_pool_size:     int

    model_config = {"from_attributes": True}
