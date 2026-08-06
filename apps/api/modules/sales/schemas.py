from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class SalesOrderLineCreate(BaseModel):
    product_id: UUID
    qty_ordered: float = Field(..., gt=0)

class SalesOrderLineResponse(BaseModel):
    id: UUID
    product_id: UUID
    qty_ordered: float
    qty_produced: float

    model_config = ConfigDict(from_attributes=True)

class SalesOrderCreate(BaseModel):
    customer_id: UUID
    order_no: str = Field(..., max_length=30)
    lines: List[SalesOrderLineCreate]

class SalesOrderResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    order_no: str
    customer_id: UUID
    status: str
    created_at: datetime
    lines: List[SalesOrderLineResponse]

    model_config = ConfigDict(from_attributes=True)

# Feasibility Schemas
class FeasibilityComponentResult(BaseModel):
    component_id: UUID
    component_name: str
    component_code: str
    available_qty: float
    required_qty: float
    shortfall_qty: float

class PurchaseOrderSuggestion(BaseModel):
    component_id: UUID
    component_code: str
    qty: float

class FeasibilityResponse(BaseModel):
    sales_order_id: UUID
    requested_qty: float
    producible_qty: float
    shortfall_qty: float
    limiting_components: List[FeasibilityComponentResult]
    readiness_pct: float
    recommended_purchase_orders: List[PurchaseOrderSuggestion]
