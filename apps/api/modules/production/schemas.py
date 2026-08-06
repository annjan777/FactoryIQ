import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class WorkOrderResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    production_order_id: uuid.UUID
    stage: str
    sequence_no: int
    status: str
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    lead_time_hours: Optional[int] = None

    class Config:
        from_attributes = True

class ProductionOrderCreate(BaseModel):
    product_id: uuid.UUID
    sales_order_id: Optional[uuid.UUID] = None
    target_qty: float
    warehouse_id: uuid.UUID
    scheduled_start: Optional[datetime] = None  # If omitted, defaults to now()

class ProductionOrderResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    org_id: uuid.UUID
    product_id: uuid.UUID
    sales_order_id: Optional[uuid.UUID] = None
    target_qty: float
    status: str
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    work_orders: List[WorkOrderResponse]

    class Config:
        from_attributes = True

class GanttBarResponse(BaseModel):
    """Flat structure suitable for Gantt chart rendering."""
    production_order_id: uuid.UUID
    work_order_id: uuid.UUID
    stage: str
    sequence_no: int
    status: str
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    lead_time_hours: Optional[int] = None

    class Config:
        from_attributes = True

