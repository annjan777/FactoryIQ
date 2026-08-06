import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Numeric, Integer, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.session import Base


class InspectionGate(Base):
    """Quality control gate rules defined per production stage or material type."""
    __tablename__ = "inspection_gates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False) # cutting, stitching, finishing, packing, grn
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sample_size_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=10.00) # e.g. 10% sample check
    max_defect_rate_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=2.00) # e.g. 2% max allowed defect rate
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class QualityInspection(Base):
    """Record of an inspection run against a WorkOrder or PurchaseOrderLine."""
    __tablename__ = "quality_inspections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    gate_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("inspection_gates.id", ondelete="SET NULL"), nullable=True)
    work_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("work_orders.id", ondelete="SET NULL"), nullable=True)
    po_line_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("purchase_order_lines.id", ondelete="SET NULL"), nullable=True)
    inspector_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    inspected_qty: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    passed_qty: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    failed_qty: Mapped[float] = mapped_column(Numeric(14, 4), default=0.0)
    defect_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result: Mapped[str] = mapped_column(String(20), default="passed") # passed, failed, conditional_pass
    inspected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    gate: Mapped[Optional["InspectionGate"]] = relationship()
    inspector: Mapped["User"] = relationship()


class ScrapLog(Base):
    """Log of scrapped or rejected units."""
    __tablename__ = "scrap_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    inspection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quality_inspections.id", ondelete="CASCADE"), nullable=False)
    qty_scrapped: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    unit_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00)
    total_scrap_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00)
    disposition: Mapped[str] = mapped_column(String(50), default="scrap") # scrap, rework, return_to_vendor
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
