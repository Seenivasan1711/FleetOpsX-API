"""Scenario Simulator API — P4-E5.

POST   /scenarios              — create + queue a scenario run
GET    /scenarios              — list all runs for this tenant
GET    /scenarios/{id}         — get run details
GET    /scenarios/{id}/status  — poll status + progress
GET    /scenarios/{id}/results — per-day KPI results
DELETE /scenarios/{id}         — cancel / delete a run
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_dispatcher
from app.schemas.scenario import ScenarioRunIn, ScenarioRunOut, ScenarioResultOut, ScenarioStatusOut
from app.services import scenario_service

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


@router.post("", response_model=ScenarioRunOut, status_code=201)
def create_scenario(
    body: ScenarioRunIn,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Create and queue a new scenario run. Returns immediately with status QUEUED."""
    if body.scenario_type not in scenario_service.VALID_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"scenario_type must be one of: {', '.join(sorted(scenario_service.VALID_TYPES))}",
        )

    run = scenario_service.create_run(
        db=db,
        tenant_id=current_user.tenant_id,
        name=body.name,
        scenario_type=body.scenario_type,
        parameters=body.parameters,
        horizon_start=body.horizon_start,
        horizon_days=body.horizon_days,
        created_by=current_user.email or str(current_user.id),
    )
    db.commit()
    db.refresh(run)

    # Queue the Celery task
    from app.workers.tasks import scenario_run_task
    scenario_run_task.apply_async(args=[str(run.id), str(current_user.tenant_id)])

    return run


@router.get("", response_model=list[ScenarioRunOut])
def list_scenarios(
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    return scenario_service.list_runs(db, current_user.tenant_id)


@router.get("/{run_id}", response_model=ScenarioRunOut)
def get_scenario(
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    run = scenario_service.get_run(db, run_id, current_user.tenant_id)
    if not run:
        raise HTTPException(status_code=404, detail="Scenario run not found")
    return run


@router.get("/{run_id}/status", response_model=ScenarioStatusOut)
def get_scenario_status(
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    run = scenario_service.get_run(db, run_id, current_user.tenant_id)
    if not run:
        raise HTTPException(status_code=404, detail="Scenario run not found")

    completed = len(scenario_service.get_results(db, run_id, current_user.tenant_id))

    return ScenarioStatusOut(
        status=run.status,
        progress=completed,
        total=run.horizon_days,
        current_date=None,  # no pub/sub in this implementation; poll results count
    )


@router.get("/{run_id}/results", response_model=list[ScenarioResultOut])
def get_scenario_results(
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    run = scenario_service.get_run(db, run_id, current_user.tenant_id)
    if not run:
        raise HTTPException(status_code=404, detail="Scenario run not found")
    return scenario_service.get_results(db, run_id, current_user.tenant_id)


@router.delete("/{run_id}", status_code=204)
def delete_scenario(
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    run = scenario_service.get_run(db, run_id, current_user.tenant_id)
    if not run:
        raise HTTPException(status_code=404, detail="Scenario run not found")
    db.delete(run)
    db.commit()
