from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PlanNoteIn(BaseModel):
    note:   str
    rating: Optional[int] = Field(None, ge=1, le=5)


class PlanNoteOut(BaseModel):
    id:              UUID
    plan_history_id: UUID
    note:            str
    rating:          Optional[int]
    created_by:      Optional[UUID]
    created_at:      datetime

    class Config:
        from_attributes = True


class PlanHistoryIn(BaseModel):
    plan_date:        date
    scenario_type:    Optional[str] = None
    source:           str = "manual"
    total_orders:     Optional[int] = None
    total_routes:     Optional[int] = None
    coverage_pct:     Optional[float] = None
    est_fuel_cost_inr: Optional[float] = None
    total_time_min:   Optional[int] = None
    ai_confidence:    Optional[float] = None


class PlanHistoryOut(BaseModel):
    id:               UUID
    plan_date:        date
    scenario_type:    Optional[str]
    source:           str
    total_orders:     Optional[int]
    total_routes:     Optional[int]
    coverage_pct:     Optional[float]
    est_fuel_cost_inr: Optional[float]
    total_time_min:   Optional[int]
    ai_confidence:    Optional[float]
    created_by:       Optional[UUID]
    created_at:       datetime
    notes:            List[PlanNoteOut] = []

    class Config:
        from_attributes = True
