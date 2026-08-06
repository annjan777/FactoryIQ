from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import List, Optional

class SupplierComponentCreate(BaseModel):
    supplier_id: UUID
    component_id: UUID
    unit_cost: float = 0.00
    lead_time_days: int = 7
    is_preferred: bool = True

class SupplierComponentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    supplier_id: UUID
    component_id: UUID
    unit_cost: float
    lead_time_days: int
    is_preferred: bool

    model_config = ConfigDict(from_attributes=True)

class MRPRequirementLine(BaseModel):
    """One row of the MRP explosion result per component."""
    component_id: UUID
    component_code: str
    component_name: str
    gross_requirement: float      # total needed across all open SOs
    available_qty: float          # current available stock
    net_requirement: float        # max(0, gross - available)
    shortfall: bool               # True if net_requirement > 0
    preferred_supplier_id: Optional[UUID] = None
    preferred_supplier_name: Optional[str] = None
    unit_cost: Optional[float] = None
    lead_time_days: Optional[int] = None

class MRPDraftPO(BaseModel):
    """A draft PO created by the MRP run."""
    po_id: UUID
    po_no: str
    supplier_id: UUID
    supplier_name: str
    line_count: int
    total_cost: float

class MRPRunResult(BaseModel):
    """Full output of a single MRP run."""
    warehouse_id: UUID
    total_components_analysed: int
    shortfall_count: int
    draft_pos_created: List[MRPDraftPO]
    requirements: List[MRPRequirementLine]
