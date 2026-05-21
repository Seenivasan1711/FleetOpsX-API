from pydantic import BaseModel
from uuid import UUID
from typing import List, Optional
from datetime import date


class PlanSummary(BaseModel):
    mode: str
    plan_id: str
    total_distance_km: float
    est_duration_min: int
    est_fuel_cost: float
    orders_covered: int
    total_orders: int = 0
    total_routes: int = 0
    # AI-enriched fields — null when no LLM is configured
    ai_summary: Optional[str] = None
    confidence_score: Optional[float] = None
    reasoning_steps: List[str] = []
    warnings: List[str] = []


class PlanOptionsResponse(BaseModel):
    plan_date: date
    options: List[PlanSummary]
    recommendation: Optional[str] = None      # mode the LLM recommends
    naive_distance_km: Optional[float] = None  # cross-mode savings baseline


class PlanConfirmRequest(BaseModel):
    plan_id: UUID
    plan_date: date
