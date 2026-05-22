"""
VehicleCollectorAgent — Phase 1 (parallel).
Fetches active vehicles for the tenant.
In E5, this will also check maintenance schedules and EV charging state.
"""
from __future__ import annotations

import logging
import time
from uuid import UUID

from sqlalchemy import select

from app.planners.context import AgentContext, AgentResult

logger = logging.getLogger(__name__)


class VehicleCollectorAgent:
    name = "VehicleCollectorAgent"
    phase = 1
    execution = "parallel"

    def run(self, ctx: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        try:
            from app.models.vehicle import Vehicle

            tid = UUID(ctx["tenant_id"])
            db = ctx["db"]

            vehicles = db.execute(
                select(Vehicle).where(Vehicle.tenant_id == tid, Vehicle.is_active == True)
            ).scalars().all()

            ctx["vehicles"] = list(vehicles)

            elapsed = int((time.monotonic() - t0) * 1000)
            refrigerated = sum(1 for v in vehicles if v.is_refrigerated)
            log_entry = {
                "step": self.name,
                "role": "tool",
                "content": (
                    f"Loaded {len(vehicles)} active vehicles "
                    f"({refrigerated} refrigerated)."
                ),
            }
            ctx["logs"].append(log_entry)

            warnings = []
            if len(vehicles) == 0:
                warnings.append("No active vehicles found.")

            return AgentResult(
                agent_name=self.name,
                status="completed",
                output={
                    "total_vehicles": len(vehicles),
                    "refrigerated_vehicles": refrigerated,
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
