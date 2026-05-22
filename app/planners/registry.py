"""
Agent registry — AI-1 E1.

To add a new agent:
  1. Create app/planners/agents/my_agent.py implementing PlanningAgent.
  2. Import and append it to the correct phase list below.
  Nothing else changes — the runner reads these lists at startup.

Phase 1 — parallel data collection (Celery group in E6, sequential for E1)
Phase 2 — sequential planning (order matters; each agent receives Phase 1 output)
Phase 3 — parallel reasoning (asyncio.gather in E7, sequential for E1)
"""
from app.planners.agents.order_collector import OrderCollectorAgent
from app.planners.agents.driver_collector import DriverCollectorAgent
from app.planners.agents.vehicle_collector import VehicleCollectorAgent
from app.planners.agents.forecast_agent import ForecastAgent
from app.planners.agents.ortools_optimizer import ORToolsOptimizerAgent
from app.planners.agents.baseline_computer import BaselineComputerAgent
from app.planners.agents.explain_agent import ExplainAgent
from app.planners.agents.risk_scorer import RiskScorerAgent

# ─── Phase 1 — all run (conceptually) in parallel ─────────────────────────────
PHASE_1_AGENTS = [
    OrderCollectorAgent(),
    DriverCollectorAgent(),
    VehicleCollectorAgent(),
    ForecastAgent(),
    # E4: ConstraintValidatorAgent() — add here once built
    # E5: CarryForwardLoaderAgent() — add here once built
]

# ─── Phase 2 — sequential, each needs Phase 1 complete ────────────────────────
PHASE_2_AGENTS = [
    # E4: ConstraintValidatorAgent() — validates instructions against plan context
    ORToolsOptimizerAgent(),
    BaselineComputerAgent(),   # runs after ORToolsOptimizer, needs plan_result + ctx["orders"]
]

# ─── Phase 3 — all run (conceptually) in parallel ─────────────────────────────
PHASE_3_AGENTS = [
    ExplainAgent(),
    RiskScorerAgent(),
    # E5: CarryForwardAgent() — add here once built
    # E4: LearningUpdaterAgent() — add here once built
]
