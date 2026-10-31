"""Billing Execution Log — records each billing engine run."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, Text, Numeric
from app.database import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


class BillingExecutionLog(Base):
    __tablename__ = "billing_execution_logs"

    id = Column(String(36), primary_key=True, default=_uuid)
    run_type = Column(String(20), default="scheduled")  # scheduled | manual
    started_at = Column(DateTime(timezone=True), default=_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    subscriptions_due = Column(Integer, default=0)
    invoices_generated = Column(Integer, default=0)
    invoices_failed = Column(Integer, default=0)
    invoices_skipped = Column(Integer, default=0)
    total_billed = Column(Numeric(14, 2), default=0)
    status = Column(String(20), default="running")  # running | completed | failed
    error_details = Column(Text, nullable=True)
    created_by = Column(String(36), nullable=True)
