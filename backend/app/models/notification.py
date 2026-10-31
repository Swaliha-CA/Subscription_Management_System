"""Notification model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    notification_type = Column(String(50), nullable=False)  # payment_reminder | renewal | invoice | etc.
    subject = Column(String(300), nullable=False)
    body = Column(Text, nullable=False)
    reference_id = Column(String(36), nullable=True)   # invoice/subscription ID
    reference_type = Column(String(50), nullable=True) # invoice | subscription
    is_read = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    send_status = Column(String(20), default="pending")  # pending | sent | failed | dev_mode
    created_at = Column(DateTime(timezone=True), default=_now)

    customer = relationship("Customer", back_populates="notifications")
    user = relationship("User", foreign_keys=[user_id])
