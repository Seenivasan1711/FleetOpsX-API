"""
Celery tasks — P4-E2 + P4-E4 + P4-E5.

Tasks:
  - deliver_webhook_task   : POST event payload to partner URL, HMAC-signed
                             Retries: 30s → 5min → 1hr → give up
  - data_export_task       : ZIP all tenant data for GDPR export (P4-E4)
  - retention_sweep_task   : Soft-delete records older than retention_days (P4-E4)
  - scenario_run_task      : Run baseline + scenario planning async (P4-E5)
"""
import hashlib
import hmac
import json
import logging
from uuid import UUID

import httpx

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

RETRY_BACKOFF = [30, 300, 3600]  # seconds: 30s, 5min, 1hr


@celery_app.task(
    bind=True,
    max_retries=3,
    name="deliver_webhook",
)
def deliver_webhook_task(self, webhook_id: str, event_type: str, payload: dict):
    """Deliver a webhook event to a registered partner URL.

    Signed with HMAC-SHA256 using the webhook's secret. Retries on failure
    with exponential backoff (30s → 5min → 1hr).
    """
    from app.core.db import SessionLocal
    from app.core.db import decrypt_connection_string
    from app.models.integration import WebhookRegistration
    from sqlalchemy import select

    db = SessionLocal()
    try:
        webhook = db.execute(
            select(WebhookRegistration).where(
                WebhookRegistration.id == UUID(webhook_id),
                WebhookRegistration.is_active == True,
            )
        ).scalar_one_or_none()

        if not webhook:
            logger.warning("deliver_webhook: webhook %s not found or inactive", webhook_id)
            return

        body = json.dumps({"event": event_type, "data": payload}, default=str)

        headers = {"Content-Type": "application/json", "X-FleetOpsX-Event": event_type}

        # HMAC-SHA256 signature if secret is set
        if webhook.secret:
            try:
                secret = decrypt_connection_string(webhook.secret)
                sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
                headers["X-FleetOpsX-Signature"] = f"sha256={sig}"
            except Exception:
                pass  # deliver unsigned if decryption fails

        with httpx.Client(timeout=10.0) as client:
            resp = client.post(webhook.url, content=body, headers=headers)
            resp.raise_for_status()

        # Clear last_error on success
        if webhook.last_error:
            webhook.last_error = None
            db.commit()

        logger.info("deliver_webhook: %s → %s [%d]", event_type, webhook.url, resp.status_code)

    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        retry_num = self.request.retries
        countdown = RETRY_BACKOFF[retry_num] if retry_num < len(RETRY_BACKOFF) else RETRY_BACKOFF[-1]
        err_msg = str(exc)
        logger.warning("deliver_webhook: %s → %s failed (%s), retry %d/%d in %ds",
                       event_type, webhook_id, err_msg, retry_num + 1, self.max_retries, countdown)

        # Persist last_error
        try:
            webhook = db.execute(
                select(WebhookRegistration).where(WebhookRegistration.id == UUID(webhook_id))
            ).scalar_one_or_none()
            if webhook:
                webhook.last_error = err_msg
                db.commit()
        except Exception:
            pass

        raise self.retry(exc=exc, countdown=countdown)

    except Exception as exc:
        logger.error("deliver_webhook: unexpected error for %s: %s", webhook_id, exc, exc_info=True)
        raise

    finally:
        db.close()


# ─── P4-E4: GDPR data export ──────────────────────────────────────────────────

@celery_app.task(name="data_export", bind=True, max_retries=1)
def data_export_task(self, tenant_id: str) -> dict:
    """Generate a ZIP archive of all tenant data for GDPR export.

    The ZIP is written to /tmp and the file path is returned as download_url.
    In production this should be uploaded to S3/GCS and a pre-signed URL returned.
    """
    import io
    import json as _json
    import zipfile
    import tempfile
    import os
    from app.core.db import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        tables = [
            "orders", "drivers", "vehicles", "depots", "route_plans",
            "routes", "route_stops", "integration_logs", "audit_log_entries",
        ]
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".zip", prefix=f"export_{tenant_id[:8]}_"
        )
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
            for table in tables:
                try:
                    rows = db.execute(
                        text(f"SELECT * FROM {table} WHERE tenant_id = :tid"),
                        {"tid": tenant_id},
                    ).mappings().all()
                    zf.writestr(
                        f"{table}.json",
                        _json.dumps([dict(r) for r in rows], default=str),
                    )
                except Exception as exc:
                    logger.warning("data_export: table=%s error=%s", table, exc)
        tmp.close()
        logger.info("data_export: tenant=%s → %s", tenant_id, tmp.name)
        return {"download_url": f"file://{tmp.name}"}
    finally:
        db.close()


# ─── P4-E4: Retention sweep ───────────────────────────────────────────────────

@celery_app.task(name="retention_sweep")
def retention_sweep_task() -> dict:
    """Daily job: soft-delete (or hard-delete) records older than each tenant's retention_days.

    Covers: audit_log_entries, integration_logs, agent_logs (oldest cost to store).
    """
    from datetime import timedelta, datetime, timezone
    from app.core.db import SessionLocal
    from app.models.tenant import Tenant, TenantConfig
    from sqlalchemy import select, delete as sa_delete
    from app.models.audit_log import AuditLogEntry
    from app.models.integration import IntegrationLog
    from app.models.agent_log import AgentLog

    db = SessionLocal()
    summary: dict[str, int] = {}
    try:
        tenants = db.execute(select(Tenant).where(Tenant.is_active == True)).scalars().all()
        for tenant in tenants:
            cfg = db.execute(
                select(TenantConfig).where(
                    TenantConfig.tenant_id == tenant.id,
                    TenantConfig.key == "retention_days",
                )
            ).scalar_one_or_none()
            days = int(cfg.value) if cfg else 365
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            deleted = 0
            for model in (AuditLogEntry, IntegrationLog, AgentLog):
                result = db.execute(
                    sa_delete(model).where(
                        model.tenant_id == tenant.id,
                        model.created_at < cutoff,
                    )
                )
                deleted += result.rowcount

            if deleted:
                db.commit()
                summary[str(tenant.slug)] = deleted
                logger.info("retention_sweep: tenant=%s deleted=%d (cutoff=%s)", tenant.slug, deleted, cutoff.date())

    except Exception as exc:
        logger.error("retention_sweep: error=%s", exc, exc_info=True)
        db.rollback()
    finally:
        db.close()

    return summary


# ─── P4-E5: Scenario run ──────────────────────────────────────────────────────

@celery_app.task(name="scenario_run", bind=True, max_retries=0)
def scenario_run_task(self, run_id: str, tenant_id: str) -> dict:
    """Execute baseline + scenario planning and persist per-day KPI results.

    commit_assignments=False is used throughout — scenario runs never mutate
    production order/route data.
    """
    from uuid import UUID as _UUID
    from app.core.db import SessionLocal
    from app.services.scenario_service import execute_run

    db = SessionLocal()
    try:
        execute_run(db=db, run_id=_UUID(run_id), tenant_id=_UUID(tenant_id))
        return {"run_id": run_id, "status": "COMPLETED"}
    except Exception as exc:
        logger.error("scenario_run_task: run=%s error=%s", run_id, exc, exc_info=True)
        return {"run_id": run_id, "status": "FAILED", "error": str(exc)}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# P5-E2: AI Scenario Generation Task
# ---------------------------------------------------------------------------

@celery_app.task(name="ai_scenario_task", bind=True, max_retries=0)
def ai_scenario_task(self, tenant_id: str, plan_date_str: str, nl_constraints: str | None = None) -> dict:
    """Generate plan options using OR-Tools + LLM enrichment (grounded, not hallucinated)."""
    from datetime import date as _date
    from app.core.db import SessionLocal
    from app.services.plan_options_service import generate_options

    db = SessionLocal()
    try:
        plan_date = _date.fromisoformat(plan_date_str)
        response = generate_options(db=db, tenant_id=tenant_id, plan_date=plan_date)
        # Shape result to match legacy polling contract so existing FE polling still works
        scenarios = [
            {
                "type": opt.mode,
                "kpis": {
                    "total_distance_km": opt.total_distance_km,
                    "est_duration_min": opt.est_duration_min,
                    "est_fuel_cost": opt.est_fuel_cost,
                    "orders_covered": opt.orders_covered,
                    "total_orders": opt.total_orders,
                    "total_routes": opt.total_routes,
                },
                "plan_id": opt.plan_id,
                "ai_summary": opt.ai_summary,
                "confidence_score": opt.confidence_score,
                "reasoning_steps": opt.reasoning_steps,
                "warnings": opt.warnings,
            }
            for opt in response.options
        ]
        return {
            "status": "done",
            "result": {
                "scenarios": scenarios,
                "recommendation": response.recommendation,
                "naive_distance_km": response.naive_distance_km,
            },
        }
    except Exception as exc:
        logger.error("ai_scenario_task error: %s", exc, exc_info=True)
        return {"status": "failed", "error": str(exc)}
    finally:
        db.close()
