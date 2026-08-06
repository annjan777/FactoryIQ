from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from db.session import get_db
from modules.auth.dependencies import get_current_user
from modules.auth.models import User
from modules.admin.schemas import (
    TenantAdminResponse,
    TenantStatusUpdate,
    TenantSubscriptionUpdate,
    SystemStatsResponse,
)

@router.post("/tenants/{tenant_id}/subscription", response_model=TenantAdminResponse)
async def update_tenant_subscription(
    tenant_id: uuid.UUID,
    payload: TenantSubscriptionUpdate,
    _: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Update tenant subscription status, expiration date, industry, or product limit."""
    try:
        updated = await AdminService.update_subscription(db, tenant_id, payload)
        tenants = await AdminService.list_tenants(db)
        return next(t for t in tenants if t.id == updated.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/tenants/{tenant_id}/kill-switch", response_model=TenantAdminResponse)
async def toggle_kill_switch(
    tenant_id: uuid.UUID,
    _: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Toggle tenant kill-switch: immediately suspend active tenant or reactivate suspended tenant."""
    try:
        tenants = await AdminService.list_tenants(db)
        tenant_record = next((t for t in tenants if t.id == tenant_id), None)
        if not tenant_record:
            raise HTTPException(status_code=404, detail="Tenant not found.")

        target_status = "suspended" if tenant_record.status == "active" else "active"
        updated = await AdminService.update_tenant_status(db, tenant_id, target_status)
        tenants_refreshed = await AdminService.list_tenants(db)
        return next(t for t in tenants_refreshed if t.id == updated.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

from modules.admin.service import AdminService

router = APIRouter(prefix="/admin", tags=["Superadmin Portal"])


async def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Verifies that the requesting user is a platform superadmin."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin privileges required.",
        )
    return current_user


@router.get("/tenants", response_model=List[TenantAdminResponse])
async def list_all_tenants(
    _: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Global system endpoint listing all registered tenants and user counts."""
    return await AdminService.list_tenants(db)


@router.patch("/tenants/{tenant_id}/status", response_model=TenantAdminResponse)
async def update_tenant_status(
    tenant_id: uuid.UUID,
    payload: TenantStatusUpdate,
    _: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Suspend or reactivate a tenant account across the system."""
    try:
        updated = await AdminService.update_tenant_status(
            db, tenant_id, payload.status
        )
        tenants = await AdminService.list_tenants(db)
        return next(t for t in tenants if t.id == updated.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    _: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Get system-wide usage and tenant statistics."""
    return await AdminService.get_system_stats(db)
