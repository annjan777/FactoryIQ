import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class SupplierCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    contact_email: Optional[str] = Field(None, max_length=100)

class SupplierResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    org_id: uuid.UUID
    code: str
    name: str
    contact_email: Optional[str]

    class Config:
        from_attributes = True

class POLineCreate(BaseModel):
    component_id: uuid.UUID
    qty_ordered: float
    unit_cost: float = 0.00

class POLineResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    po_id: uuid.UUID
    component_id: uuid.UUID
    qty_ordered: float
    unit_cost: float

    class Config:
        from_attributes = True

class POCreate(BaseModel):
    supplier_id: uuid.UUID
    po_no: str = Field(..., max_length=50)
    lines: List[POLineCreate]

class POResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    org_id: uuid.UUID
    supplier_id: uuid.UUID
    po_no: str
    status: str
    created_at: datetime
    updated_at: datetime
    lines: List[POLineResponse]

    class Config:
        from_attributes = True
