"""
Failure classifier — AI-1 E6.

Classifies any exception from a planning agent as either:
  "transient" — temporary condition; Celery should auto-retry
  "blocker"   — genuine problem requiring dispatcher attention

Transient examples: DB connection timeout, LLM rate-limit (429), OSError.
Blocker  examples: data validation error, missing config, ORTools infeasible.
"""
from __future__ import annotations

from typing import Literal

# Celery retry backoff schedule (seconds): 30s → 2min → 10min
TRANSIENT_BACKOFF = [30, 120, 600]


def classify_failure(exc: Exception) -> Literal["transient", "blocker"]:
    """Return 'transient' if auto-retry is appropriate, 'blocker' otherwise."""
    exc_type = type(exc).__name__
    message = str(exc).lower()

    # ── Transient: DB / network / rate-limit ──────────────────────────────────
    if exc_type in (
        "OperationalError",       # SQLAlchemy DB connection / timeout
        "DisconnectionError",
        "TimeoutError",
        "ConnectionError",
        "ConnectionRefusedError",
        "ConnectionResetError",
        "OSError",
        "BrokenPipeError",
        "RemoteDisconnected",
        "ReadTimeout",
        "ConnectTimeout",
    ):
        return "transient"

    # LLM rate-limit signals
    if any(kw in message for kw in ("rate limit", "429", "too many requests", "quota exceeded")):
        return "transient"

    # Redis / Celery broker connectivity
    if any(kw in message for kw in ("redis", "broker", "amqp", "connection refused")):
        return "transient"

    # ── Blocker: data / config / logic errors ─────────────────────────────────
    if exc_type in (
        "ValueError",
        "KeyError",
        "AttributeError",
        "TypeError",
        "AssertionError",
        "NotImplementedError",
        "PermissionError",
    ):
        return "blocker"

    # OR-Tools infeasibility signals
    if any(kw in message for kw in ("infeasible", "no solution", "constraint violation")):
        return "blocker"

    # Default: treat unknowns as blocker (don't retry endlessly)
    return "blocker"
