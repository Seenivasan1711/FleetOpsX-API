"""Scenario service — P4-E5: Multi-Day Planning & Scenario Simulator."""
import logging
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scenario import ScenarioRun, ScenarioResult

logger = logging.getLogger(__name__)

VALID_TYPES = {"new_depot", "ev_fleet_mix", "driver_count_change", "demand_surge"}


def create_run(
    db: Session,
    tenant_id: UUID,
    name: str,
    scenario_type: str,
    parameters: dict,
    horizon_start: date,
    horizon_days: int,
    created_by: str,
) -> ScenarioRun:
    run = ScenarioRun(
        tenant_id=tenant_id,
        name=name,
        scenario_type=scenario_type,
        parameters=parameters,
        horizon_start=horizon_start,
        horizon_days=horizon_days,
        created_by=created_by,
        status="QUEUED",
    )
    db.add(run)
    db.flush()
    return run


def get_run(db: Session, run_id: UUID, tenant_id: UUID) -> ScenarioRun | None:
    return db.execute(
        select(ScenarioRun).where(
            ScenarioRun.id == run_id,
            ScenarioRun.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()


def list_runs(db: Session, tenant_id: UUID) -> list[ScenarioRun]:
    return db.execute(
        select(ScenarioRun)
        .where(ScenarioRun.tenant_id == tenant_id)
        .order_by(ScenarioRun.created_at.desc())
    ).scalars().all()


def get_results(db: Session, run_id: UUID, tenant_id: UUID) -> list[ScenarioResult]:
    run = get_run(db, run_id, tenant_id)
    if not run:
        return []
    return db.execute(
        select(ScenarioResult)
        .where(ScenarioResult.scenario_run_id == run_id)
        .order_by(ScenarioResult.plan_date)
    ).scalars().all()


def _kpis_from_result(day_result: dict) -> dict:
    """Extract per-day KPIs from a plan_day result dict."""
    assigned = day_result.get("assigned_orders", 0)
    total    = max(day_result.get("total_orders", 1), 1)
    routes   = day_result.get("total_routes", 0)
    dist_km  = day_result.get("total_distance_km", 0.0)

    on_time_rate = assigned / total if total else 0.0
    # Rough fleet utilisation: assigned / (routes * 12 stops avg capacity)
    fleet_util = min(assigned / max(routes * 12, 1), 1.0) if routes else 0.0

    return {
        "total_routes":       routes,
        "assigned_orders":    assigned,
        "on_time_rate":       round(on_time_rate, 4),
        "avg_delay_min":      0.0,        # OR-Tools doesn't surface per-stop delay yet
        "total_distance_km":  round(dist_km, 2),
        "fleet_utilization":  round(fleet_util, 4),
    }


def execute_run(db: Session, run_id: UUID, tenant_id: UUID) -> None:
    """Run baseline + scenario and persist ScenarioResult rows.

    Called inside the Celery task so DB sessions are managed by the task.
    """
    from datetime import datetime, timezone
    from app.planners.ortools_planner import ORToolsPlanner

    run = get_run(db, run_id, tenant_id)
    if not run:
        logger.error("scenario_service.execute_run: run %s not found", run_id)
        return

    run.status = "RUNNING"
    db.commit()

    dates = [run.horizon_start + timedelta(days=i) for i in range(run.horizon_days)]
    planner = ORToolsPlanner()

    try:
        # ── Baseline run (no scenario params) ─────────────────────────────────
        baseline_days = planner.plan_horizon(
            db=db, tenant_id=str(tenant_id), dates=dates, parameters={}
        )
        baseline_kpis_per_day = [_kpis_from_result(r) for r in baseline_days]

        # Aggregate baseline KPIs
        run.baseline_kpis = {
            "avg_on_time_rate":      round(
                sum(k["on_time_rate"] for k in baseline_kpis_per_day) / len(baseline_kpis_per_day), 4
            ),
            "total_assigned_orders": sum(k["assigned_orders"] for k in baseline_kpis_per_day),
            "total_distance_km":     round(sum(k["total_distance_km"] for k in baseline_kpis_per_day), 2),
        }
        db.commit()

        # ── Scenario run ──────────────────────────────────────────────────────
        scenario_params = dict(run.parameters)
        scenario_params["_scenario_type"] = run.scenario_type

        scenario_days = planner.plan_horizon(
            db=db, tenant_id=str(tenant_id), dates=dates, parameters=scenario_params
        )

        # ── Persist per-day results with delta vs baseline ────────────────────
        for i, (d, day_result) in enumerate(zip(dates, scenario_days)):
            kpis = _kpis_from_result(day_result)
            base = baseline_kpis_per_day[i]

            kpi_delta = {
                k: round(kpis[k] - base[k], 4)
                for k in ("on_time_rate", "avg_delay_min", "fleet_utilization",
                          "total_distance_km", "assigned_orders")
            }

            result = ScenarioResult(
                tenant_id=tenant_id,
                scenario_run_id=run.id,
                plan_date=d,
                total_routes=kpis["total_routes"],
                assigned_orders=kpis["assigned_orders"],
                on_time_rate=kpis["on_time_rate"],
                avg_delay_min=kpis["avg_delay_min"],
                total_distance_km=kpis["total_distance_km"],
                fleet_utilization=kpis["fleet_utilization"],
                kpi_delta=kpi_delta,
            )
            db.add(result)

        run.status = "COMPLETED"
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("scenario run %s COMPLETED (%d days)", run_id, len(dates))

    except Exception as exc:
        logger.error("scenario run %s FAILED: %s", run_id, exc, exc_info=True)
        run.status = "FAILED"
        db.commit()
        raise
