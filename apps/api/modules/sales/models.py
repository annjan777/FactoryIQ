import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.session import Base

class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    order_no: Mapped[str] = mapped_column(String(30), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(nullable=False) # Simplified customer association
    status: Mapped[str] = mapped_column(String(20), default="open") # open, partially_produced, fulfilled, cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    tenant: Mapped["Tenant"] = relationship()
    lines: Mapped[List["SalesOrderLine"]] = relationship(back_populates="sales_order", cascade="all, delete-orphan")

class SalesOrderLine(Base):
    __tablename__ = "sales_order_lines"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sales_order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    qty_ordered: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    qty_produced: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00)

    # Relationships
    sales_order: Mapped["SalesOrder"] = relationship(back_populates="lines")
    product: Mapped["Product"] = relationship()
