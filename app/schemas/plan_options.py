from pydantic import BaseModel
from uuid import UUID
from typing import List
from datetime import date


class PlanSummary(BaseModel):
    mode: str
    plan_id: str
    total_distance_km: float
    est_duration_min: int
    est_fuel_cost: float
    orders_covered: int


class PlanOptionsResponse(BaseModel):
    plan_date: date
    options: List[PlanSummary]


class PlanConfirmRequest(BaseModel):
    plan_id: UUID
    plan_date: date
