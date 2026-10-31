"""Audit Log model — immutable record of all important system events."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=_uuid)
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    actor_email = Column(String(255), nullable=True)
    action = Column(String(100), nullable=False)         # e.g. subscription.activated
    entity_type = Column(String(50), nullable=True)      # subscription | invoice | payment | etc.
    entity_id = Column(String(36), nullable=True)
    old_values = Column(Text, nullable=True)             # JSON snapshot before change
    new_values = Column(Text, nullable=True)             # JSON snapshot after change
    ip_address = Column(String(45), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    actor = relationship("User", back_populates="audit_logs", foreign_keys=[actor_id])
