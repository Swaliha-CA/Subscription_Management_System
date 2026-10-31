"""Payment and PaymentAllocation models."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Numeric, Date
from sqlalchemy.orm import relationship
from app.database import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


PAYMENT_METHODS = ("cash", "bank_transfer", "upi", "card", "cheque", "other")
PAYMENT_STATUSES = ("pending", "confirmed", "cancelled", "refunded")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=_uuid)
    payment_number = Column(String(30), unique=True, nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    payment_method = Column(String(30), nullable=False, default="cash")
    amount = Column(Numeric(12, 2), nullable=False)
    payment_date = Column(Date, nullable=False)
    reference_number = Column(String(100), nullable=True)
    transaction_id = Column(String(200), nullable=True)
    gateway = Column(String(50), default="manual")  # manual | razorpay | stripe
    notes = Column(Text, nullable=True)
    status = Column(String(20), default="confirmed", nullable=False)
    recorded_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    customer = relationship("Customer", back_populates="payments")
    allocations = relationship("PaymentAllocation", back_populates="payment", cascade="all, delete-orphan")
    recorder = relationship("User", foreign_keys=[recorded_by])

    @property
    def allocated_amount(self) -> Decimal:
        return sum(a.amount for a in self.allocations if a.amount)

    @property
    def unallocated_amount(self) -> Decimal:
        return (self.amount or Decimal("0")) - self.allocated_amount


class PaymentAllocation(Base):
    """Links a payment to a specific invoice (supports partial/multiple payments)."""
    __tablename__ = "payment_allocations"

    id = Column(String(36), primary_key=True, default=_uuid)
    payment_id = Column(String(36), ForeignKey("payments.id"), nullable=False)
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    allocated_at = Column(DateTime(timezone=True), default=_now)

    payment = relationship("Payment", back_populates="allocations")
    invoice = relationship("Invoice", back_populates="payment_allocations")
