import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from modules.auth.models import Tenant, User
from modules.sales.models import SalesOrder
from modules.production.models import ProductionOrder
from modules.purchasing.models import PurchaseOrder
from modules.admin.schemas import TenantAdminResponse, SystemStatsResponse


class AdminService:

    @staticmethod
    async def list_tenants(db: AsyncSession) -> List[TenantAdminResponse]:
        """List all tenants with computed user count across the entire platform (bypassing tenant RLS)."""
        tenants_res = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
        tenants = tenants_res.scalars().all()

        results = []
        for t in tenants:
            cnt_res = await db.execute(
                select(func.count(User.id)).where(User.tenant_id == t.id)
            )
            u_count = cnt_res.scalar() or 0
            results.append(
                TenantAdminResponse(
                    id=t.id,
                    name=t.name,
                    subdomain=t.subdomain,
                    plan=t.plan,
                    isolation_mode=t.isolation_mode,
                    status=t.status,
                    subscription_status=t.subscription_status or "active",
                    subscription_expires_at=t.subscription_expires_at,
                    industry_type=t.industry_type or "garment",
                    max_products_limit=t.max_products_limit or 100,
                    created_at=t.created_at,
                    user_count=u_count,
                )
            )
        return results

    @staticmethod
    async def update_tenant_status(
        db: AsyncSession, tenant_id: uuid.UUID, new_status: str
    ) -> Tenant:
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")
        tenant.status = new_status
        if new_status == "suspended":
            tenant.subscription_status = "suspended"
        elif new_status == "active" and tenant.subscription_status == "suspended":
            tenant.subscription_status = "active"
        await db.commit()
        await db.refresh(tenant)
        return tenant

    @staticmethod
    async def update_subscription(
        db: AsyncSession, tenant_id: uuid.UUID, payload
    ) -> Tenant:
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")

        if payload.subscription_status is not None:
            tenant.subscription_status = payload.subscription_status
            if payload.subscription_status == "suspended":
                tenant.status = "suspended"
            elif payload.subscription_status in ["active", "trial"]:
                tenant.status = "active"

        if payload.subscription_expires_at is not None:
            tenant.subscription_expires_at = payload.subscription_expires_at
        if payload.industry_type is not None:
            tenant.industry_type = payload.industry_type
        if payload.max_products_limit is not None:
            tenant.max_products_limit = payload.max_products_limit

        await db.commit()
        await db.refresh(tenant)
        return tenant


    @staticmethod
    async def get_system_stats(db: AsyncSession) -> SystemStatsResponse:
        """Global system-wide operational metrics."""
        all_t = (await db.execute(select(func.count(Tenant.id)))).scalar() or 0
        active_t = (
            await db.execute(select(func.count(Tenant.id)).where(Tenant.status == "active"))
        ).scalar() or 0
        suspended_t = (
            await db.execute(select(func.count(Tenant.id)).where(Tenant.status == "suspended"))
        ).scalar() or 0

        tot_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
        tot_so = (await db.execute(select(func.count(SalesOrder.id)))).scalar() or 0
        tot_pro = (await db.execute(select(func.count(ProductionOrder.id)))).scalar() or 0
        tot_po = (await db.execute(select(func.count(PurchaseOrder.id)))).scalar() or 0

        return SystemStatsResponse(
            total_tenants=all_t,
            active_tenants=active_t,
            suspended_tenants=suspended_t,
            total_users=tot_users,
            total_sales_orders=tot_so,
            total_production_orders=tot_pro,
            total_purchase_orders=tot_po,
        )
