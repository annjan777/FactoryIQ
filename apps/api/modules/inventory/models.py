import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Numeric, ForeignKey, DateTime, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.session import Base

class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    component_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("components.id", ondelete="CASCADE"), nullable=False)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    on_hand_qty: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00)
    reserved_qty: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00)
    allocated_qty: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00)
    wip_qty: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00)
    damaged_qty: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00)
    in_transit_qty: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00)

    # Relationships
    tenant: Mapped["Tenant"] = relationship()
    component: Mapped["Component"] = relationship()
    warehouse: Mapped["Warehouse"] = relationship()

    @property
    def available_qty(self) -> float:
        # Available = on_hand - reserved - allocated - damaged
        return float(self.on_hand_qty) - float(self.reserved_qty) - float(self.allocated_qty) - float(self.damaged_qty)

class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    component_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("components.id", ondelete="CASCADE"), nullable=False)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(30), nullable=False) # grn, issue, reserve, release, scrap, adjustment
    qty: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False) # signed qty
    reference_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True) # purchase_order, production_order, etc.
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    batch_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    lot_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    tenant: Mapped["Tenant"] = relationship()
    component: Mapped["Component"] = relationship()
    warehouse: Mapped["Warehouse"] = relationship()

class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    component_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("components.id", ondelete="CASCADE"), nullable=False)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    source_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True) # References internal SalesOrder / ProductionOrder
    status: Mapped[str] = mapped_column(String(50), default="active") # active, fulfilled, cancelled, expired
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    tenant: Mapped["Tenant"] = relationship()
    component: Mapped["Component"] = relationship()
    warehouse: Mapped["Warehouse"] = relationship()
