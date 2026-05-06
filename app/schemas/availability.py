from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional, List
from datetime import datetime, time, date


class DriverAvailabilityUpdate(BaseModel):
    shift_start: Optional[time] = None
    shift_end: Optional[time] = None
    status: str = Field(default="available", pattern="^(available|on_break|off_duty)$")
    hours_worked_today: Optional[float] = None


class DriverAvailabilityResponse(BaseModel):
    id: UUID
    driver_id: UUID
    tenant_id: UUID
    date: date
    shift_start: Optional[time] = None
    shift_end: Optional[time] = None
    status: str
    hours_worked_today: float
    updated_at: datetime

    class Config:
        from_attributes = True


class VehicleStatusUpdate(BaseModel):
    current_mileage: Optional[float] = None
    fuel_level_pct: Optional[float] = Field(default=None, ge=0, le=100)
    status: str = Field(default="available", pattern="^(available|in_use|maintenance)$")


class VehicleStatusResponse(BaseModel):
    id: UUID
    vehicle_id: UUID
    tenant_id: UUID
    current_mileage: Optional[float] = None
    fuel_level_pct: Optional[float] = None
    status: str
    updated_at: datetime

    class Config:
        from_attributes = True


class DriverAvailabilitySummary(BaseModel):
    driver_id: UUID
    driver_name: str
    status: str
    shift_start: Optional[time] = None
    shift_end: Optional[time] = None
    hours_worked_today: float


class VehicleStatusSummary(BaseModel):
    vehicle_id: UUID
    registration_number: str
    vehicle_type: str
    status: str
    fuel_level_pct: Optional[float] = None
    current_mileage: Optional[float] = None


class FleetAvailabilityResponse(BaseModel):
    date: date
    drivers: List[DriverAvailabilitySummary]
    vehicles: List[VehicleStatusSummary]
