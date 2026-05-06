import uuid
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin, TenantMixin


class ChatMessage(Base, TimestampMixin, TenantMixin):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(100), nullable=False, index=True)
    # user | assistant
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
