from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class InspectionGateCreate(BaseModel):
    stage: str # cutting, stitching, finishing, packing, grn
    name: str
    sample_size_pct: float = 10.00
    max_defect_rate_pct: float = 2.00
    is_active: bool = True

class InspectionGateResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    stage: str
    name: str
    sample_size_pct: float
    max_defect_rate_pct: float
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class QualityInspectionCreate(BaseModel):
    gate_id: Optional[UUID] = None
    work_order_id: Optional[UUID] = None
    po_line_id: Optional[UUID] = None
    inspected_qty: float
    passed_qty: float
    failed_qty: float = 0.0
    defect_reason: Optional[str] = None
    disposition: Optional[str] = "scrap" # scrap, rework, return_to_vendor

class QualityInspectionResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    gate_id: Optional[UUID]
    work_order_id: Optional[UUID]
    po_line_id: Optional[UUID]
    inspector_id: UUID
    inspected_qty: float
    passed_qty: float
    failed_qty: float
    defect_reason: Optional[str]
    result: str
    inspected_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ScrapLogResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    inspection_id: UUID
    qty_scrapped: float
    unit_cost: float
    total_scrap_cost: float
    disposition: str
    notes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
