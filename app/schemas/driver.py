from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime, time


class DriverBase(BaseModel):
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    license_number: Optional[str] = None
    license_class: Optional[str] = None
    default_shift_start: Optional[time] = None
    default_shift_end: Optional[time] = None
    home_depot_id: Optional[UUID] = None
    is_active: bool = True


class DriverCreate(DriverBase):
    pass


class DriverUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    home_depot_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    default_shift_start: Optional[time] = None
    default_shift_end: Optional[time] = None


class DriverResponse(DriverBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    utilization_pct: Optional[float] = None
    performance_score: Optional[float] = None

    class Config:
        from_attributes = True
