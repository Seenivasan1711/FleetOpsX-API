"""
DriverCollectorAgent — Phase 1 (parallel).
Fetches active drivers with availability checks (shift + availability table).
Populates ctx["drivers"] and ctx["driver_availability_3day"].

In E5, driver_availability_3day will be extended to cover Day+1 and Day+2.
For E1, it contains only today's data.
"""
from __future__ import annotations

import logging
import time
from uuid import UUID

from sqlalchemy import select

from app.planners.context import AgentContext, AgentResult

logger = logging.getLogger(__name__)


class DriverCollectorAgent:
    name = "DriverCollectorAgent"
    phase = 1
    execution = "parallel"

    def run(self, ctx: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        try:
            from app.models.driver import Driver
            from app.models.driver_shift import DriverShift
            from app.models.driver_availability import DriverAvailability

            tid = UUID(ctx["tenant_id"])
            plan_date = ctx["plan_date"]
            db = ctx["db"]

            all_drivers = db.execute(
                select(Driver).where(Driver.tenant_id == tid, Driver.is_active == True)
            ).scalars().all()

            shifts = db.execute(
                select(DriverShift).where(
                    DriverShift.tenant_id == tid,
                    DriverShift.shift_date == plan_date,
                )
            ).scalars().all()
            shift_unavailable = {s.driver_id for s in shifts if s.status != "WORKING"}

            avail_records = db.execute(
                select(DriverAvailability).where(
                    DriverAvailability.tenant_id == tid,
                    DriverAvailability.date == plan_date,
                )
            ).scalars().all()
            avail_unavailable = {r.driver_id for r in avail_records if r.status != "available"}

            unavailable_ids = shift_unavailable | avail_unavailable
            available_drivers = [d for d in all_drivers if d.id not in unavailable_ids]

            ctx["drivers"] = available_drivers

            # Build driver_availability_3day — Day 0 only for E1 (E5 extends to Day+1, Day+2)
            avail_map: dict[str, dict] = {}
            for d in available_drivers:
                avail_map[str(d.id)] = {
                    "day0": "available",
                    "day0_name": d.full_name,
                }
            ctx["driver_availability_3day"] = avail_map

            elapsed = int((time.monotonic() - t0) * 1000)
            on_leave = len(all_drivers) - len(available_drivers)
            log_entry = {
                "step": self.name,
                "role": "tool",
                "content": (
                    f"Loaded {len(available_drivers)} available drivers "
                    f"(of {len(all_drivers)} total, {on_leave} unavailable) for {plan_date}."
                ),
            }
            ctx["logs"].append(log_entry)

            warnings = []
            if len(available_drivers) == 0:
                warnings.append("No available drivers for this date.")

            return AgentResult(
                agent_name=self.name,
                status="completed",
                output={
                    "total_drivers": len(all_drivers),
                    "available_drivers": len(available_drivers),
                    "unavailable_drivers": on_leave,
                },
                warnings=warnings,
                elapsed_ms=elapsed,
                log_entry=log_entry,
            )

        except Exception as exc:
            elapsed = int((time.monotonic() - t0) * 1000)
            logger.exception("%s failed: %s", self.name, exc)
            log_entry = {"step": self.name, "role": "tool", "content": f"ERROR: {exc}"}
            ctx["logs"].append(log_entry)
            return AgentResult(
                agent_name=self.name,
                status="failed",
                output={},
                warnings=[str(exc)],
                elapsed_ms=elapsed,
                log_entry=log_entry,
            )
