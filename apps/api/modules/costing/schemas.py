from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional

class StandardCostCreate(BaseModel):
    product_id: Optional[UUID] = None
    component_id: Optional[UUID] = None
    std_material_cost: float = 0.00
    std_labor_cost: float = 0.00
    std_overhead_cost: float = 0.00

class StandardCostResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    product_id: Optional[UUID]
    component_id: Optional[UUID]
    std_material_cost: float
    std_labor_cost: float
    std_overhead_cost: float
    std_total_cost: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class JobCostSummaryResponse(BaseModel):
    production_order_id: UUID
    product_id: UUID
    target_qty: float
    actual_material_cost: float
    actual_labor_cost: float
    actual_overhead_cost: float
    actual_total_cost: float
    std_total_cost: float
    cost_variance: float
    is_favorable: bool
    unit_cost_actual: float
    unit_cost_standard: float
