"""
APScheduler setup — P3-E1 (ETL) + P3-E3 (Monitor scan) + P4-E1 (DB route refresh) + P4-E3 (Marketplace) + P4-E4 (Retention)

Jobs (all UTC):
  - daily_etl           @ 01:00 daily        → analytics ETL for all tenants
  - monitor_scan        @ every 5 min 07–20  → Monitor Agent SLA scan for all tenants
  - db_route_refresh    @ every 60s           → refresh per-tenant DB routing cache (P4-E1)
  - marketplace_match   @ every 5 min 06–22  → Capacity Marketplace greedy match engine (P4-E3)
  - retention_sweep     @ 02:00 daily        → delete records beyond tenant retention window (P4-E4)

Runs inside the FastAPI process (BackgroundScheduler).
Start/stop managed via FastAPI asynccontextmanager lifespan.
"""
import logging
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, refresh_route_cache
from app.models.tenant import Tenant
from app.services.analytics_service import run_etl

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


# ─── ETL job ──────────────────────────────────────────────────────────────────

def _run_etl_all_tenants() -> None:
    """ETL job: processes yesterday's data for all active tenants."""
    from datetime import timedelta
    etl_date = date.today() - timedelta(days=1)
    db: Session = SessionLocal()
    try:
        tenants = db.query(Tenant).filter(Tenant.is_active == True).all()
        logger.info("Scheduled ETL: processing %d tenants for %s", len(tenants), etl_date)
        for tenant in tenants:
            try:
                result = run_etl(db=db, tenant_id=str(tenant.id), etl_date=etl_date)
                logger.info("ETL tenant=%s date=%s result=%s", tenant.slug, etl_date, result)
            except Exception as exc:
                logger.error("ETL failed tenant=%s: %s", tenant.slug, exc, exc_info=True)
    finally:
        db.close()


# ─── Monitor scan job ─────────────────────────────────────────────────────────

def _run_monitor_all_tenants() -> None:
    """Monitor scan: check at-risk stops for all active tenants — today's date."""
    from app.planners.agents.monitor_agent import run_monitor_scan
    plan_date = date.today()
    db: Session = SessionLocal()
    try:
        tenants = db.query(Tenant).filter(Tenant.is_active == True).all()
        for tenant in tenants:
            try:
                created = run_monitor_scan(db=db, tenant_id=str(tenant.id), plan_date=plan_date)
                if created:
                    logger.info("Monitor scan tenant=%s: %d suggestions created", tenant.slug, created)
            except Exception as exc:
                logger.error("Monitor scan failed tenant=%s: %s", tenant.slug, exc, exc_info=True)
    finally:
        db.close()


# ─── Marketplace match engine (P4-E3) ────────────────────────────────────────

def _run_marketplace_match() -> None:
    """Run the greedy zone-match engine for the Capacity Marketplace."""
    from app.services.marketplace_service import run_match_engine
    db: Session = SessionLocal()
    try:
        count = run_match_engine(db)
        if count:
            logger.info("Marketplace match engine: %d new match(es) created", count)
    except Exception as exc:
        logger.error("Marketplace match engine error: %s", exc, exc_info=True)
    finally:
        db.close()


# ─── Retention sweep (P4-E4) ─────────────────────────────────────────────────

def _run_retention_sweep() -> None:
    """Dispatch the retention_sweep Celery task (runs daily @ 02:00 UTC)."""
    from app.workers.tasks import retention_sweep_task
    retention_sweep_task.apply_async()
    logger.info("Retention sweep task queued")


# ─── DB route cache refresh job (P4-E1) ──────────────────────────────────────

def _refresh_db_routes() -> None:
    """Reload per-tenant DB routing table into memory every 60 seconds."""
    db: Session = SessionLocal()
    try:
        count = refresh_route_cache(db)
        if count:
            logger.debug("DB route cache refresh: %d dedicated routes active", count)
    except Exception as exc:
        logger.warning("DB route cache refresh error: %s", exc)
    finally:
        db.close()


# ─── Scheduler lifecycle ──────────────────────────────────────────────────────

def start_scheduler() -> None:
    """Register all jobs and start the scheduler. Called from FastAPI lifespan."""
    scheduler.add_job(
        _run_etl_all_tenants,
        trigger=CronTrigger(hour=1, minute=0),
        id="daily_etl",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _run_monitor_all_tenants,
        trigger=CronTrigger(hour="7-20", minute="*/5"),
        id="monitor_scan",
        replace_existing=True,
        misfire_grace_time=120,
    )
    scheduler.add_job(
        _refresh_db_routes,
        trigger="interval",
        seconds=60,
        id="db_route_refresh",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_marketplace_match,
        trigger=CronTrigger(hour="6-22", minute="*/5"),
        id="marketplace_match",
        replace_existing=True,
        misfire_grace_time=120,
    )
    scheduler.add_job(
        _run_retention_sweep,
        trigger=CronTrigger(hour=2, minute=0),
        id="retention_sweep",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info(
        "APScheduler started — daily ETL @ 01:00 UTC, monitor scan every 5 min (07–20 UTC), "
        "DB route refresh every 60s, marketplace match every 5 min (06–22 UTC), "
        "retention sweep @ 02:00 UTC (P4-E4)"
    )


def stop_scheduler() -> None:
    """Graceful shutdown. Called from FastAPI lifespan shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")
