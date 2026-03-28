from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime


class VehicleBase(BaseModel):
    registration_number: str
    vehicle_type: str = "VAN"
    capacity_kg: Optional[float] = None
    capacity_volume_liters: Optional[float] = None
    capacity_units: Optional[int] = None
    is_refrigerated: bool = False
    home_depot_id: Optional[UUID] = None
    is_active: bool = True


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    registration_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    capacity_kg: Optional[float] = None
    is_refrigerated: Optional[bool] = None
    home_depot_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class VehicleResponse(VehicleBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
