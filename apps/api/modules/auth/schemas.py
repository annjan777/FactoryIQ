from pydantic import BaseModel, EmailStr, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List

# Tenant Schemas
class TenantBase(BaseModel):
    name: str = Field(..., max_length=200)
    subdomain: str = Field(..., max_length=63)
    plan: Optional[str] = "standard"
    isolation_mode: Optional[str] = "rls"

class TenantCreate(TenantBase):
    pass

class TenantResponse(TenantBase):
    id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Organization Schemas
class OrganizationBase(BaseModel):
    name: str = Field(..., max_length=200)
    industry: Optional[str] = "garment"

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationResponse(OrganizationBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# User Schemas
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserResponse(UserBase):
    id: UUID
    tenant_id: UUID
    org_id: UUID
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Role Schemas
class RoleBase(BaseModel):
    name: str = Field(..., max_length=50)
    permissions: List[str] = []

class RoleCreate(RoleBase):
    pass

class RoleResponse(RoleBase):
    id: UUID
    tenant_id: UUID

    model_config = ConfigDict(from_attributes=True)

# Token Schemas
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    tenant_id: Optional[str] = None
    org_id: Optional[str] = None
    role: Optional[str] = None
