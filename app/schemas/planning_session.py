from datetime import date, datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    plan_date: date
    hints: List[str] = Field(default_factory=list)


class RoundCreate(BaseModel):
    hints: List[str] = Field(default_factory=list)


class ConfirmRequest(BaseModel):
    plan_id: UUID


class PlanningSessionOut(BaseModel):
    id: UUID
    plan_date: date
    status: str
    cutoff_at: datetime
    active_plan_id: Optional[UUID]
    accumulated_hints: List[str]
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    def model_post_init(self, __context: Any) -> None:
        if self.accumulated_hints is None:
            object.__setattr__(self, "accumulated_hints", [])


class PlanVersionSummary(BaseModel):
    plan_id: Optional[UUID]
    version_number: int
    status: str
    km_saved: Optional[float]
    hrs_saved: Optional[float]
    total_orders: int
    assigned_orders: int
    round_hints: List[str]
    created_at: datetime

    class Config:
        from_attributes = True

    def model_post_init(self, __context: Any) -> None:
        if self.round_hints is None:
            object.__setattr__(self, "round_hints", [])


class SessionWithPlanOut(BaseModel):
    session: PlanningSessionOut
    plan: dict


class SessionDetailOut(BaseModel):
    session: PlanningSessionOut
    versions: List[PlanVersionSummary]
