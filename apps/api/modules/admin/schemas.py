from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import List, Optional

class TenantAdminResponse(BaseModel):
    id: UUID
    name: str
    subdomain: str
    plan: str
    isolation_mode: str
    status: str
    created_at: datetime
    user_count: int

    model_config = ConfigDict(from_attributes=True)

class TenantStatusUpdate(BaseModel):
    status: str # active, suspended

class SystemStatsResponse(BaseModel):
    total_tenants: int
    active_tenants: int
    suspended_tenants: int
    total_users: int
    total_sales_orders: int
    total_production_orders: int
    total_purchase_orders: int

class AuditLogItem(BaseModel):
    id: UUID
    tenant_id: Optional[UUID]
    tenant_name: Optional[str]
    event_type: str
    description: str
    timestamp: datetime
