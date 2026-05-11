"""
MongoDB Motor async client — Phase 6 (chat history)

Collections:
  chat_conversations: { _id, tenant_id, user_id, title, created_at, updated_at }
  chat_messages:      { _id, conversation_id, role, content, card_data, created_at }
"""
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: Optional[AsyncIOMotorClient] = None


def get_mongo_client() -> Optional[AsyncIOMotorClient]:
    return _client


def get_mongo_db() -> Optional[AsyncIOMotorDatabase]:
    from app.core.config import settings
    if _client is None:
        return None
    return _client[settings.MONGODB_DB]


def connect_mongo() -> None:
    global _client
    from app.core.config import settings
    if not settings.MONGODB_URL:
        return
    _client = AsyncIOMotorClient(settings.MONGODB_URL)


def disconnect_mongo() -> None:
    global _client
    if _client:
        _client.close()
        _client = None
