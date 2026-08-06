from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

class InventoryBase(BaseModel):
    component_id: UUID
    warehouse_id: UUID
    on_hand_qty: float = Field(0.0, ge=0)
    reserved_qty: float = Field(0.0, ge=0)
    allocated_qty: float = Field(0.0, ge=0)
    wip_qty: float = Field(0.0, ge=0)
    damaged_qty: float = Field(0.0, ge=0)
    in_transit_qty: float = Field(0.0, ge=0)

class InventoryResponse(InventoryBase):
    id: UUID
    tenant_id: UUID
    available_qty: float

    model_config = ConfigDict(from_attributes=True)

class InventoryAdjustment(BaseModel):
    component_id: UUID
    warehouse_id: UUID
    qty: float # Can be positive (GRN, adjustment up) or negative (scrap, issue)
    movement_type: str = Field(..., description="grn, issue, adjustment, scrap")
    reference_type: Optional[str] = None
    reference_id: Optional[UUID] = None
    batch_no: Optional[str] = None
    lot_no: Optional[str] = None

class StockMovementResponse(BaseModel):
    id: int
    tenant_id: UUID
    component_id: UUID
    warehouse_id: UUID
    movement_type: str
    qty: float
    reference_type: Optional[str]
    reference_id: Optional[UUID]
    batch_no: Optional[str]
    lot_no: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ReservationCreate(BaseModel):
    component_id: UUID
    warehouse_id: UUID
    quantity: float = Field(..., gt=0)
    source_order_id: Optional[UUID] = None
    expires_at: Optional[datetime] = None

class ReservationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    component_id: UUID
    warehouse_id: UUID
    quantity: float
    source_order_id: Optional[UUID]
    status: str
    expires_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class InventoryTransferCreate(BaseModel):
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    component_id: UUID
    qty: float = Field(..., gt=0)
