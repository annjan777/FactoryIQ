from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List

# Warehouse Schemas
class WarehouseCreate(BaseModel):
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=100)

class WarehouseResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    org_id: UUID
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)

# Component Schemas
class ComponentCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    uom: str = Field(..., max_length=20)
    reorder_level: float = Field(0.0, ge=0)
    safety_stock: float = Field(0.0, ge=0)

class ComponentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    org_id: UUID
    code: str
    name: str
    uom: str
    reorder_level: float
    safety_stock: float

    model_config = ConfigDict(from_attributes=True)

# Product Schemas
class ProductCreate(BaseModel):
    sku: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    category: Optional[str] = Field(None, max_length=50)

class ProductResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    org_id: UUID
    sku: str
    name: str
    category: Optional[str]

    model_config = ConfigDict(from_attributes=True)

# BOM Line Schemas
class BOMLineCreate(BaseModel):
    component_id: UUID
    qty_per_unit: float = Field(..., gt=0)
    scrap_pct: float = Field(0.0, ge=0, le=100)

class BOMLineResponse(BaseModel):
    id: UUID
    component_id: UUID
    qty_per_unit: float
    scrap_pct: float
    component: ComponentResponse

    model_config = ConfigDict(from_attributes=True)

# BOM Header Schemas
class BOMCreate(BaseModel):
    product_id: UUID
    version: int = 1
    is_active: bool = True
    lines: List[BOMLineCreate]

class BOMResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    product_id: UUID
    version: int
    is_active: bool
    lines: List[BOMLineResponse]

    model_config = ConfigDict(from_attributes=True)
