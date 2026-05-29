"""
OrderCollectorAgent — Phase 1 (parallel).
Fetches pending orders for the plan date.
In E5 this will also load carry_forward_notes from the previous day.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from app.planners.context import AgentContext, AgentResult

logger = logging.getLogger(__name__)


class OrderCollectorAgent:
    name = "OrderCollectorAgent"
    phase = 1
    execution = "parallel"

    def run(self, ctx: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        try:
            from app.models.order import Order

            tid = UUID(ctx["tenant_id"])
            plan_date = ctx["plan_date"]
            day_start = datetime.combine(plan_date, datetime.min.time())
            day_end = day_start + timedelta(days=1)

            orders = ctx["db"].execute(
                select(Order).where(
                    Order.tenant_id == tid,
                    Order.status == "PENDING",
                    Order.scheduled_date >= day_start,
                    Order.scheduled_date < day_end,
                )
            ).scalars().all()

            ctx["orders"] = list(orders)
            elapsed = int((time.monotonic() - t0) * 1000)

            high_priority = sum(1 for o in orders if o.priority in ("HIGH", "CRITICAL"))
            with_windows = sum(1 for o in orders if o.time_window_start)

            # E5: carry_forward_orders pre-loaded by runner before Phase 1
            cf_count = len(ctx.get("carry_forward_orders", []))

            log_entry = {
                "step": self.name,
                "role": "tool",
                "content": (
                    f"Loaded {len(orders)} pending orders for {plan_date}. "
                    f"{high_priority} high/critical priority, "
                    f"{with_windows} with time windows. "
                    f"{cf_count} carry-forward note(s) from previous day."
                ),
            }
            ctx["logs"].append(log_entry)

            return AgentResult(
                agent_name=self.name,
                status="completed",
                output={
                    "total_orders": len(orders),
                    "high_priority": high_priority,
                    "with_time_windows": with_windows,
                    "carry_forward_notes": cf_count,
                },
                warnings=[],
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
