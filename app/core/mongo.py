"""
MongoDB Motor async client — Phase 6 (chat history)

Optional: only connects when MONGODB_URL is set in environment.
If not configured, all conversation endpoints gracefully return empty data
and fall back to the existing Postgres-backed chat.

Collections (when MongoDB is active):
  chat_conversations: { _id, tenant_id, user_id, title, created_at, updated_at }
  chat_messages:      { _id, conversation_id, role, content, card_data, created_at }
"""
import logging
from typing import TYPE_CHECKING, Any, Optional

logger = logging.getLogger(__name__)

# Motor is an optional dependency — guard the import so the service starts
# even when motor/pymongo are not installed yet.
try:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase as _MotorDB
    _MOTOR_AVAILABLE = True
except ImportError:
    AsyncIOMotorClient = None  # type: ignore[assignment,misc]
    _MotorDB = None
    _MOTOR_AVAILABLE = False
    logger.warning(
        "motor package not installed — MongoDB chat history is disabled. "
        "Install motor>=3.4 and set MONGODB_URL to enable."
    )

_client: Optional[Any] = None
_mongodb_active: bool = False


def is_mongo_active() -> bool:
    """Returns True when Motor client is connected."""
    return _mongodb_active


def get_mongo_db() -> Optional[Any]:
    """Returns the Motor database handle, or None if MongoDB is not configured."""
    if not _mongodb_active or _client is None:
        return None
    from app.core.config import settings
    return _client[settings.MONGODB_DB]


def connect_mongo() -> None:
    """Connect Motor client. No-op (and no error) when MONGODB_URL is absent."""
    global _client, _mongodb_active
    if not _MOTOR_AVAILABLE:
        return
    from app.core.config import settings
    if not settings.MONGODB_URL:
        logger.info("MONGODB_URL not set — chat history will use in-session fallback")
        return
    try:
        _client = AsyncIOMotorClient(settings.MONGODB_URL)
        _mongodb_active = True
        logger.info("MongoDB Motor client connected (%s)", settings.MONGODB_URL.split("@")[-1])
    except Exception as exc:
        logger.warning("MongoDB connection failed (chat will use fallback): %s", exc)
        _client = None
        _mongodb_active = False


def disconnect_mongo() -> None:
    global _client, _mongodb_active
    if _client:
        _client.close()
    _client = None
    _mongodb_active = False
