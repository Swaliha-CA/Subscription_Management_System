"""Quotation Template, Quotation, and QuotationLine models."""
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


QUOTATION_STATUSES = ("draft", "sent", "confirmed", "expired", "cancelled")


class QuotationTemplate(Base):
    __tablename__ = "quotation_templates"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(200), nullable=False)
    plan_id = Column(String(36), ForeignKey("subscription_plans.id"), nullable=True)
    validity_days = Column(Integer, default=30)
    payment_terms = Column(String(100), default="Due on receipt")
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    plan = relationship("SubscriptionPlan")
    quotations = relationship("Quotation", back_populates="template")


class Quotation(Base):
    __tablename__ = "quotations"

    id = Column(String(36), primary_key=True, default=_uuid)
    quotation_number = Column(String(30), unique=True, nullable=False)
    template_id = Column(String(36), ForeignKey("quotation_templates.id"), nullable=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    plan_id = Column(String(36), ForeignKey("subscription_plans.id"), nullable=True)
    status = Column(String(30), default="draft", nullable=False)
    validity_days = Column(Integer, default=30)
    expiry_date = Column(Date, nullable=True)
    payment_terms = Column(String(100), default="Due on receipt")
    notes = Column(Text, nullable=True)
    subtotal = Column(Numeric(12, 2), default=Decimal("0.00"))
    tax_amount = Column(Numeric(12, 2), default=Decimal("0.00"))
    discount_amount = Column(Numeric(12, 2), default=Decimal("0.00"))
    grand_total = Column(Numeric(12, 2), default=Decimal("0.00"))
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    confirmed_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    template = relationship("QuotationTemplate", back_populates="quotations")
    customer = relationship("Customer", back_populates="quotations")
    plan = relationship("SubscriptionPlan", back_populates="quotations")
    lines = relationship("QuotationLine", back_populates="quotation", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="quotation", uselist=False)
    creator = relationship("User", foreign_keys=[created_by])
    confirmer = relationship("User", foreign_keys=[confirmed_by])


class QuotationLine(Base):
    __tablename__ = "quotation_lines"

    id = Column(String(36), primary_key=True, default=_uuid)
    quotation_id = Column(String(36), ForeignKey("quotations.id"), nullable=False)
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

    quotation = relationship("Quotation", back_populates="lines")
    product = relationship("Product")
    variant = relationship("ProductVariant")
