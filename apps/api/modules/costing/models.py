import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.session import Base


class StandardCost(Base):
    """Standard cost target defined per product SKU or raw component."""
    __tablename__ = "standard_costs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    component_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("components.id", ondelete="SET NULL"), nullable=True)
    
    std_material_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00)
    std_labor_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00)
    std_overhead_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00)
    std_total_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class JobCostLedger(Base):
    """Actual cost ledger record compiled per production job run."""
    __tablename__ = "job_cost_ledger"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    production_order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("production_orders.id", ondelete="CASCADE"), nullable=False)
    
    actual_material_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00)
    actual_labor_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00)
    actual_overhead_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00)
    actual_total_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00)
    
    std_total_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00)
    cost_variance: Mapped[float] = mapped_column(Numeric(14, 2), default=0.00) # actual - standard
    is_favorable: Mapped[bool] = mapped_column(default=True) # True if actual <= standard
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
