"""Product and ProductVariant models."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Numeric, Integer
from sqlalchemy.orm import relationship
from app.database import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(200), nullable=False, index=True)
    product_type = Column(String(50), nullable=False, default="software")
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    sales_price = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    cost_price = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    plans = relationship("SubscriptionPlan", back_populates="product")
    taxes = relationship("Tax", secondary="product_taxes", back_populates="products")


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(String(36), primary_key=True, default=_uuid)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    name = Column(String(200), nullable=False)
    sku = Column(String(100), nullable=True, unique=True)
    price_modifier = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    product = relationship("Product", back_populates="variants")

    @property
    def effective_price(self) -> Decimal:
        """Base sales price of parent product plus this variant's modifier."""
        if self.product:
            return (self.product.sales_price or Decimal("0")) + (self.price_modifier or Decimal("0"))
        return self.price_modifier or Decimal("0")
