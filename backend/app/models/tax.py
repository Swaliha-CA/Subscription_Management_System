"""Tax model and product-tax association table."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Numeric, Table, Date
from sqlalchemy.orm import relationship
from app.database import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


# Association table — products ↔ taxes (many-to-many)
product_taxes = Table(
    "product_taxes",
    Base.metadata,
    Column("product_id", String(36), ForeignKey("products.id"), primary_key=True),
    Column("tax_id", String(36), ForeignKey("taxes.id"), primary_key=True),
)


class Tax(Base):
    __tablename__ = "taxes"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(100), nullable=False)
    percentage = Column(Numeric(6, 3), nullable=False)  # e.g. 18.000 for 18%
    tax_type = Column(String(50), default="GST")        # GST | VAT | CGST | etc.
    description = Column(Text, nullable=True)
    active_from = Column(Date, nullable=True)
    active_until = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    products = relationship("Product", secondary="product_taxes", back_populates="taxes")
