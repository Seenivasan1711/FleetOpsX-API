"""
DriverCollectorAgent — Phase 1 (parallel).
Fetches active drivers with availability checks (shift + availability table).

E5: driver_availability_3day now covers Day 0 (today), Day+1, Day+2 for all
active drivers — not just today's available subset. CarryForwardAgent uses this
to suggest which driver can pick up a dropped order tomorrow or the day after.

ctx["drivers"]                → available today
ctx["driver_availability_3day"] → all drivers × 3-day window
"""
from __future__ import annotations

import logging
import time
from datetime import timedelta
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
            day1 = plan_date + timedelta(days=1)
            day2 = plan_date + timedelta(days=2)
            db = ctx["db"]

            all_drivers = db.execute(
                select(Driver).where(Driver.tenant_id == tid, Driver.is_active == True)
            ).scalars().all()

            # ── Availability for all 3 days ────────────────────────────────────
            unavailable_by_day: dict[int, set] = {0: set(), 1: set(), 2: set()}
            for offset, target_date in enumerate([plan_date, day1, day2]):
                shifts = db.execute(
                    select(DriverShift).where(
                        DriverShift.tenant_id == tid,
                        DriverShift.shift_date == target_date,
                    )
                ).scalars().all()
                unavailable_by_day[offset].update(
                    s.driver_id for s in shifts if s.status != "WORKING"
                )

                avail_records = db.execute(
                    select(DriverAvailability).where(
                        DriverAvailability.tenant_id == tid,
                        DriverAvailability.date == target_date,
                    )
                ).scalars().all()
                unavailable_by_day[offset].update(
                    r.driver_id for r in avail_records if r.status != "available"
                )

            available_drivers = [
                d for d in all_drivers if d.id not in unavailable_by_day[0]
            ]
            ctx["drivers"] = available_drivers

            # ── 3-day map: keyed by driver_id string, covers all active drivers ─
            avail_map: dict[str, dict] = {}
            for d in all_drivers:
                avail_map[str(d.id)] = {
                    "name": getattr(d, "full_name", str(d.id)),
                    "day0": "unavailable" if d.id in unavailable_by_day[0] else "available",
                    "day1": "unavailable" if d.id in unavailable_by_day[1] else "available",
                    "day2": "unavailable" if d.id in unavailable_by_day[2] else "available",
                }
            ctx["driver_availability_3day"] = avail_map

            elapsed = int((time.monotonic() - t0) * 1000)
            on_leave = len(all_drivers) - len(available_drivers)
            avail_day1 = sum(1 for v in avail_map.values() if v["day1"] == "available")
            avail_day2 = sum(1 for v in avail_map.values() if v["day2"] == "available")

            log_entry = {
                "step": self.name,
                "role": "tool",
                "content": (
                    f"Loaded {len(available_drivers)} available drivers today "
                    f"(of {len(all_drivers)} total, {on_leave} unavailable). "
                    f"3-day outlook: Day+1={avail_day1} available, Day+2={avail_day2} available."
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
                    "available_day1": avail_day1,
                    "available_day2": avail_day2,
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
