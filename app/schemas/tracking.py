"""Tracking schemas — P2-E4."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class PingIn(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy_m: Optional[float] = None
    speed_kmh: Optional[float] = None
    heading_deg: Optional[float] = None
    vehicle_id: Optional[UUID] = None


class PingOut(BaseModel):
    id: UUID
    driver_id: UUID
    latitude: float
    longitude: float
    accuracy_m: Optional[float]
    speed_kmh: Optional[float]
    heading_deg: Optional[float]
    recorded_at: datetime

    model_config = {"from_attributes": True}


class LivePositionOut(BaseModel):
    driver_id: str
    driver_name: str
    latitude: float
    longitude: float
    accuracy_m: Optional[float] = None
    speed_kmh: Optional[float] = None
    heading_deg: Optional[float] = None
    recorded_at: str
