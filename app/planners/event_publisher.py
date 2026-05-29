"""
Planning run event publisher — AI-1 E7.

Publishes structured events to Redis pub/sub channel:
  planning:run:{run_id}:events

Called synchronously from runner.py (which runs in a sync context).
The WebSocket handler subscribes asynchronously via redis.asyncio.

Event envelope:
{
  "type": "run_started" | "agent_started" | "agent_completed" |
          "phase_completed" | "run_completed" | "run_failed" | "heartbeat",
  "run_id": "<uuid>",
  "data": { ... type-specific fields ... },
  "ts": "<iso8601>"
}
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_CHANNEL_PREFIX = "planning:run"


def channel_name(run_id: str) -> str:
    return f"{_CHANNEL_PREFIX}:{run_id}:events"


def publish_event(run_id: str, event_type: str, data: dict) -> None:
    """Publish a planning run event to Redis. Fire-and-forget; never raises."""
    if not run_id:
        return
    try:
        from app.core.redis import redis_client
        event = {
            "type": event_type,
            "run_id": run_id,
            "data": data,
            "ts": datetime.utcnow().isoformat(),
        }
        redis_client.publish(channel_name(run_id), json.dumps(event, default=str))
    except Exception as exc:
        logger.debug("publish_event[%s] %s failed (non-fatal): %s", run_id[:8], event_type, exc)
