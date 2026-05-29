"""
Planning run WebSocket — AI-1 E7.

Endpoint: GET /ws/planning-run/{run_id}?token=<jwt>

Streams live planning progress events to the client by subscribing to:
  Redis channel: planning:run:{run_id}:events

Event types the client receives:
  run_started       — pipeline about to begin
  phase_started     — phase N starting (agent_count included)
  agent_started     — an agent is now running (progress_pct = before-agent %)
  agent_completed   — agent finished (status, elapsed_ms, output_preview, progress_pct)
  phase_completed   — all agents in phase finished
  run_completed     — 100% done (client should fetch GET /plan/runs/{run_id} for results)
  run_failed        — unrecoverable failure (error_type, message)
  heartbeat         — sent every 30s when idle to keep the connection alive

Late-joiner handling:
  If the run is already COMPLETED / FAILED when the client connects, a synthetic
  terminal event is sent immediately so the client doesn't hang waiting.

Auth: JWT passed as ?token=<jwt> query parameter (same as /ws/events).
"""
from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from app.core.config import settings
from app.planners.event_publisher import channel_name

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Planning WebSocket"])


@router.websocket("/ws/planning-run/{run_id}")
async def ws_planning_run(
    ws: WebSocket,
    run_id: UUID,
    token: str = Query(..., description="JWT access token"),
):
    """
    Subscribe to live agent-level progress events for a planning run.
    Closes automatically when run_completed or run_failed is received.
    """
    from app.core.security import decode_token

    # ── Auth ──────────────────────────────────────────────────────────────────
    try:
        payload = decode_token(token)
        tenant_id: str = str(payload.get("tenant_id", ""))
        if not tenant_id or tenant_id == "None":
            await ws.close(code=4001, reason="No tenant")
            return
    except JWTError:
        await ws.close(code=4001, reason="Invalid token")
        return

    await ws.accept()

    # ── Late-joiner: check if run already terminal ────────────────────────────
    terminal_event = await _check_terminal(str(run_id), tenant_id)
    if terminal_event:
        await ws.send_text(json.dumps(terminal_event))
        await ws.close()
        return

    # ── Subscribe to Redis pub/sub ────────────────────────────────────────────
    import redis.asyncio as aioredis  # redis-py 4.2+ ships this

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    channel = channel_name(str(run_id))
    await pubsub.subscribe(channel)

    try:
        forward_task = asyncio.create_task(_forward_events(pubsub, ws, str(run_id)))
        receive_task = asyncio.create_task(_receive_client(ws))

        done, pending = await asyncio.wait(
            {forward_task, receive_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    except WebSocketDisconnect:
        logger.info("ws_planning_run: client disconnected run_id=%s", run_id)
    except Exception as exc:
        logger.warning("ws_planning_run: unexpected error run_id=%s: %s", run_id, exc)
    finally:
        await pubsub.unsubscribe(channel)
        await r.aclose()


# ── Internal coroutines ────────────────────────────────────────────────────────

async def _forward_events(pubsub, ws: WebSocket, run_id: str) -> None:
    """Read from Redis, forward to WebSocket. Returns when run terminates or connection drops."""
    heartbeat = json.dumps({"type": "heartbeat", "run_id": run_id})
    while True:
        # 30s timeout — send heartbeat if no event arrives
        msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
        if msg is None:
            await ws.send_text(heartbeat)
            continue

        data_str: str = msg["data"]
        await ws.send_text(data_str)

        try:
            parsed = json.loads(data_str)
            if parsed.get("type") in ("run_completed", "run_failed"):
                return  # terminal event — stop forwarding
        except Exception:
            pass


async def _receive_client(ws: WebSocket) -> None:
    """Handle client messages (ping/pong). Exits on disconnect."""
    while True:
        text = await ws.receive_text()
        if text == "ping":
            await ws.send_text(json.dumps({"type": "pong"}))


async def _check_terminal(run_id: str, tenant_id: str) -> dict | None:
    """
    Return a synthetic terminal event if the run is already COMPLETED/FAILED,
    so late-joining clients don't hang waiting for events that already fired.
    """
    try:
        import asyncio as _asyncio
        from app.core.db import SessionLocal
        from app.models.planning_run import PlanningRun
        from uuid import UUID as _UUID

        def _query():
            db = SessionLocal()
            try:
                return db.get(PlanningRun, _UUID(run_id))
            finally:
                db.close()

        loop = _asyncio.get_event_loop()
        run = await loop.run_in_executor(None, _query)

        if run and run.tenant_id == _UUID(tenant_id):
            if run.status == "COMPLETED":
                return {"type": "run_completed", "run_id": run_id, "data": {"progress_pct": 100.0}, "ts": run.completed_at.isoformat() if run.completed_at else ""}
            if run.status in ("FAILED", "BLOCKED_WAITING_USER"):
                err = run.error_info or {}
                return {"type": "run_failed", "run_id": run_id, "data": {"status": run.status, "message": err.get("message", "")}, "ts": run.completed_at.isoformat() if run.completed_at else ""}
    except Exception as exc:
        logger.debug("_check_terminal failed (non-fatal): %s", exc)
    return None
