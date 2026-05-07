"""Schemas for P4-E5: Multi-Day Planning & Scenario Simulator."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScenarioRunIn(BaseModel):
    name:           str
    scenario_type:  str = Field(..., description="new_depot | ev_fleet_mix | driver_count_change | demand_surge")
    parameters:     dict[str, Any] = {}
    horizon_start:  date
    horizon_days:   int = Field(default=7, ge=1, le=14)


class ScenarioRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             UUID
    name:           str
    scenario_type:  str
    parameters:     dict[str, Any]
    horizon_start:  date
    horizon_days:   int
    status:         str
    baseline_kpis:  Any | None = None
    created_by:     str
    completed_at:   datetime | None = None
    tenant_id:      UUID
    created_at:     datetime


class ScenarioStatusOut(BaseModel):
    status:       str
    progress:     int
    total:        int
    current_date: str | None = None


class ScenarioResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                UUID
    plan_date:         date
    total_routes:      int
    assigned_orders:   int
    on_time_rate:      float
    avg_delay_min:     float
    total_distance_km: float
    fleet_utilization: float
    kpi_delta:         Any | None = None


# Multi-day plan
class MultiDayPlanRequest(BaseModel):
    start_date:   date
    horizon_days: int = Field(default=5, ge=1, le=14)
    parameters:   dict[str, Any] = {}


class DayPlanSummary(BaseModel):
    plan_date:       date
    plan_id:         str | None
    assigned_orders: int
    total_routes:    int
    total_orders:    int


class MultiDayPlanResult(BaseModel):
    days:    list[DayPlanSummary]
    summary: dict[str, Any]
