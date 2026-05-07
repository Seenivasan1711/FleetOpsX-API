"""
Cost model weights per plan mode — PP-E2.

Each mode adjusts the OR-Tools arc cost function and the fuel-cost rate
used to compute the human-facing plan summary metrics.

  fastest    – minimises travel time; higher fuel spend accepted
  economical – minimises km driven; lower fuel spend, potentially longer day
  balanced   – equal time/distance trade-off
"""

PLAN_MODES = ("fastest", "economical", "balanced")

# Weights applied to (time_minutes, distance_km) when building the arc cost
# matrix fed to OR-Tools.  Values are scaled to integers inside the planner.
MODE_WEIGHTS: dict[str, dict] = {
    "fastest": {
        "time_weight": 1.0,
        "dist_weight": 0.1,
        "fuel_cost_per_km": 0.12,   # $/km — faster routing burns more fuel
    },
    "economical": {
        "time_weight": 0.1,
        "dist_weight": 1.0,
        "fuel_cost_per_km": 0.08,   # $/km — route minimises distance
    },
    "balanced": {
        "time_weight": 0.5,
        "dist_weight": 0.5,
        "fuel_cost_per_km": 0.10,   # $/km — middle ground
    },
}


def get_weights(plan_mode: str) -> dict:
    if plan_mode not in MODE_WEIGHTS:
        raise ValueError(f"Unknown plan_mode {plan_mode!r}. Use: {', '.join(PLAN_MODES)}")
    return MODE_WEIGHTS[plan_mode]
