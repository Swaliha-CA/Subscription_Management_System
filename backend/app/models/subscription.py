"""Subscription, SubscriptionLine, and BillingCycle models."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Numeric, Integer, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


SUBSCRIPTION_STATUSES = ("draft", "quotation", "confirmed", "active", "paused", "closed", "expired")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=_uuid)
    subscription_number = Column(String(30), unique=True, nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    plan_id = Column(String(36), ForeignKey("subscription_plans.id"), nullable=False)
    quotation_id = Column(String(36), ForeignKey("quotations.id"), nullable=True)
    status = Column(String(20), default="draft", nullable=False, index=True)
    start_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    next_billing_date = Column(Date, nullable=True, index=True)
    payment_terms = Column(String(100), default="Due on receipt")
    quantity = Column(Numeric(10, 2), nullable=False, default=Decimal("1.00"))
    unit_price = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    tax_pct = Column(Numeric(6, 3), default=Decimal("0.000"))
    discount_pct = Column(Numeric(6, 3), default=Decimal("0.000"))
    discount_id = Column(String(36), ForeignKey("discounts.id"), nullable=True)
    subtotal = Column(Numeric(12, 2), default=Decimal("0.00"))
    tax_amount = Column(Numeric(12, 2), default=Decimal("0.00"))
    discount_amount = Column(Numeric(12, 2), default=Decimal("0.00"))
    total_amount = Column(Numeric(12, 2), default=Decimal("0.00"))
    notes = Column(Text, nullable=True)
    paused_at = Column(DateTime(timezone=True), nullable=True)
    resumed_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    customer = relationship("Customer", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    quotation = relationship("Quotation", back_populates="subscription")
    lines = relationship("SubscriptionLine", back_populates="subscription", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="subscription")
    billing_cycles = relationship("BillingCycle", back_populates="subscription", cascade="all, delete-orphan")
    discount = relationship("Discount", foreign_keys=[discount_id])
    creator = relationship("User", foreign_keys=[created_by])


class SubscriptionLine(Base):
    __tablename__ = "subscription_lines"

    id = Column(String(36), primary_key=True, default=_uuid)
    subscription_id = Column(String(36), ForeignKey("subscriptions.id"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    variant_id = Column(String(36), ForeignKey("product_variants.id"), nullable=True)
    description = Column(Text, nullable=True)
    quantity = Column(Numeric(10, 2), nullable=False, default=Decimal("1.00"))
    unit_price = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    discount_pct = Column(Numeric(6, 3), default=Decimal("0.000"))
    tax_pct = Column(Numeric(6, 3), default=Decimal("0.000"))
    subtotal = Column(Numeric(12, 2), default=Decimal("0.00"))
    tax_amount = Column(Numeric(12, 2), default=Decimal("0.00"))
    total = Column(Numeric(12, 2), default=Decimal("0.00"))

    subscription = relationship("Subscription", back_populates="lines")
    product = relationship("Product")
    variant = relationship("ProductVariant")


class BillingCycle(Base):
    """Tracks each billed period for a subscription — prevents duplicate billing."""
    __tablename__ = "billing_cycles"
    __table_args__ = (
        UniqueConstraint("subscription_id", "cycle_start", "cycle_end", name="uq_billing_cycle"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    subscription_id = Column(String(36), ForeignKey("subscriptions.id"), nullable=False)
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=True)
    cycle_start = Column(Date, nullable=False)
    cycle_end = Column(Date, nullable=False)
    billed_at = Column(DateTime(timezone=True), default=_now)
    status = Column(String(20), default="billed")  # billed | failed | skipped

    subscription = relationship("Subscription", back_populates="billing_cycles")
    invoice = relationship("Invoice")
