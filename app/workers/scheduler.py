"""
APScheduler setup — P3-E1 (ETL) + P3-E3 (Monitor scan)

Jobs (all UTC):
  - daily_etl       @ 01:00 daily        → analytics ETL for all tenants
  - monitor_scan    @ every 5 min 07–20  → Monitor Agent SLA scan for all tenants

Runs inside the FastAPI process (BackgroundScheduler).
Start/stop managed via FastAPI asynccontextmanager lifespan.
"""
import logging
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
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
    scheduler.start()
    logger.info("APScheduler started — daily ETL @ 01:00 UTC, monitor scan every 5 min (07–20 UTC)")


def stop_scheduler() -> None:
    """Graceful shutdown. Called from FastAPI lifespan shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")
