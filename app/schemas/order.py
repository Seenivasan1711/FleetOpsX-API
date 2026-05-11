from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from decimal import Decimal
from datetime import datetime, time


class OrderBase(BaseModel):
    external_ref: Optional[str] = None
    customer_id: Optional[UUID] = None
    pickup_address: Optional[str] = None
    pickup_latitude: Optional[float] = None
    pickup_longitude: Optional[float] = None
    delivery_address: str
    delivery_latitude: Optional[float] = None
    delivery_longitude: Optional[float] = None
    scheduled_date: datetime
    time_window_start: Optional[time] = None
    time_window_end: Optional[time] = None
    weight_kg: Optional[float] = None
    volume_liters: Optional[float] = None
    quantity_units: Optional[int] = None
    requires_refrigeration: bool = False
    priority: str = "NORMAL"
    value: Optional[Decimal] = None
    notes: Optional[str] = None


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    delivery_address: Optional[str] = None
    delivery_latitude: Optional[float] = None
    delivery_longitude: Optional[float] = None
    scheduled_date: Optional[datetime] = None
    time_window_start: Optional[time] = None
    time_window_end: Optional[time] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None


class OrderResponse(OrderBase):
    id: UUID
    tenant_id: UUID
    status: str
    assigned_driver_id: Optional[UUID] = None
    assigned_vehicle_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
