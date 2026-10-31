"""Invoice and InvoiceLine models."""
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


INVOICE_STATUSES = ("draft", "confirmed", "paid", "partially_paid", "overdue", "cancelled")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=_uuid)
    invoice_number = Column(String(30), unique=True, nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    subscription_id = Column(String(36), ForeignKey("subscriptions.id"), nullable=True)
    status = Column(String(20), default="draft", nullable=False, index=True)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    billing_period_start = Column(Date, nullable=True)
    billing_period_end = Column(Date, nullable=True)
    subtotal = Column(Numeric(12, 2), default=Decimal("0.00"))
    tax_amount = Column(Numeric(12, 2), default=Decimal("0.00"))
    discount_amount = Column(Numeric(12, 2), default=Decimal("0.00"))
    grand_total = Column(Numeric(12, 2), default=Decimal("0.00"))
    paid_amount = Column(Numeric(12, 2), default=Decimal("0.00"))
    outstanding_amount = Column(Numeric(12, 2), default=Decimal("0.00"))
    payment_terms = Column(String(100), default="Due on receipt")
    notes = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    customer = relationship("Customer", back_populates="invoices")
    subscription = relationship("Subscription", back_populates="invoices")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")
    payment_allocations = relationship("PaymentAllocation", back_populates="invoice")
    creator = relationship("User", foreign_keys=[created_by])

    @property
    def is_overdue(self) -> bool:
        from datetime import date
        return (
            self.status not in ("paid", "cancelled")
            and self.due_date is not None
            and self.due_date < date.today()
            and float(self.outstanding_amount or 0) > 0
        )


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id = Column(String(36), primary_key=True, default=_uuid)
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=True)
    variant_id = Column(String(36), ForeignKey("product_variants.id"), nullable=True)
    description = Column(Text, nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False, default=Decimal("1.00"))
    unit_price = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    discount_pct = Column(Numeric(6, 3), default=Decimal("0.000"))
    tax_pct = Column(Numeric(6, 3), default=Decimal("0.000"))
    subtotal = Column(Numeric(12, 2), default=Decimal("0.00"))
    tax_amount = Column(Numeric(12, 2), default=Decimal("0.00"))
    total = Column(Numeric(12, 2), default=Decimal("0.00"))

    invoice = relationship("Invoice", back_populates="lines")
    product = relationship("Product")
    variant = relationship("ProductVariant")
