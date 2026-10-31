"""Discount and DiscountApplication models."""
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


class Discount(Base):
    __tablename__ = "discounts"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(200), nullable=False)
    code = Column(String(50), unique=True, nullable=True)
    discount_type = Column(String(20), nullable=False)  # fixed | percentage
    value = Column(Numeric(12, 2), nullable=False)
    min_purchase_amount = Column(Numeric(12, 2), default=Decimal("0.00"))
    min_quantity = Column(Numeric(10, 2), default=Decimal("1.00"))
    applicable_to_subscription = Column(Boolean, default=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    max_usage_count = Column(Integer, nullable=True)
    current_usage_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    applicable_products = relationship(
        "Product",
        secondary="discount_products",
    )
    applications = relationship("DiscountApplication", back_populates="discount")
    creator = relationship("User", foreign_keys=[created_by])


# Association table — discounts ↔ products (many-to-many, optional scope)
from sqlalchemy import Table
discount_products = Table(
    "discount_products",
    Base.metadata,
    Column("discount_id", String(36), ForeignKey("discounts.id"), primary_key=True),
    Column("product_id", String(36), ForeignKey("products.id"), primary_key=True),
)


class DiscountApplication(Base):
    __tablename__ = "discount_applications"

    id = Column(String(36), primary_key=True, default=_uuid)
    discount_id = Column(String(36), ForeignKey("discounts.id"), nullable=False)
    subscription_id = Column(String(36), ForeignKey("subscriptions.id"), nullable=True)
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=True)
    amount_saved = Column(Numeric(12, 2), nullable=False)
    applied_at = Column(DateTime(timezone=True), default=_now)
    applied_by = Column(String(36), ForeignKey("users.id"), nullable=True)

    discount = relationship("Discount", back_populates="applications")
    subscription = relationship("Subscription")
    invoice = relationship("Invoice")
    applier = relationship("User", foreign_keys=[applied_by])
