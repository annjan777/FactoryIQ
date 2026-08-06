import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Numeric, ForeignKey, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.session import Base

class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship()
    organization: Mapped["Organization"] = relationship()

class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship()
    boms: Mapped[List["BOMHeader"]] = relationship(back_populates="product", cascade="all, delete-orphan")

class Component(Base):
    __tablename__ = "components"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    uom: Mapped[str] = mapped_column(String(20), nullable=False) # pcs, mtr, kg, etc.
    reorder_level: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00)
    safety_stock: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00)

    # Relationships
    tenant: Mapped["Tenant"] = relationship()

class BOMHeader(Base):
    __tablename__ = "bom_headers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship()
    product: Mapped["Product"] = relationship(back_populates="boms")
    lines: Mapped[List["BOMLine"]] = relationship(back_populates="bom_header", cascade="all, delete-orphan")

class BOMLine(Base):
    __tablename__ = "bom_lines"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bom_header_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bom_headers.id", ondelete="CASCADE"), nullable=False)
    component_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("components.id", ondelete="CASCADE"), nullable=False)
    qty_per_unit: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    scrap_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0.00)

    # Relationships
    bom_header: Mapped["BOMHeader"] = relationship(back_populates="lines")
    component: Mapped["Component"] = relationship()
