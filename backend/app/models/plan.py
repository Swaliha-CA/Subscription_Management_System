"""Subscription Plan and Plan Pricing models."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Numeric, Integer, Date
from sqlalchemy.orm import relationship
from app.database import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


BILLING_FREQUENCIES = ("daily", "weekly", "monthly", "yearly")


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(200), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    billing_frequency = Column(String(20), nullable=False, default="monthly")
    base_price = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    min_quantity = Column(Integer, nullable=False, default=1)
    available_from = Column(Date, nullable=True)
    available_until = Column(Date, nullable=True)
    auto_close_on_expiry = Column(Boolean, default=True)
    allow_early_cancellation = Column(Boolean, default=True)
    allow_pause = Column(Boolean, default=True)
    allow_renewal = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    product = relationship("Product", back_populates="plans")
    pricing = relationship("PlanPricing", back_populates="plan", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="plan")
    quotations = relationship("Quotation", back_populates="plan")


class PlanPricing(Base):
    """Optional tiered/variant-specific pricing overrides for a plan."""
    __tablename__ = "plan_pricing"

    id = Column(String(36), primary_key=True, default=_uuid)
    plan_id = Column(String(36), ForeignKey("subscription_plans.id"), nullable=False)
    variant_id = Column(String(36), ForeignKey("product_variants.id"), nullable=True)
    min_qty = Column(Integer, default=1)
    max_qty = Column(Integer, nullable=True)
    unit_price = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)

    plan = relationship("SubscriptionPlan", back_populates="pricing")
    variant = relationship("ProductVariant")
