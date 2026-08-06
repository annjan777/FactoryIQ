import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from modules.costing.models import StandardCost, JobCostLedger
from modules.costing.schemas import StandardCostCreate, JobCostSummaryResponse
from modules.production.models import ProductionOrder
from modules.bom.models import BOMHeader, BOMLine


# Stage hourly labor rates ($/hour)
STAGE_LABOR_RATES = {
    "cutting": 15.00,
    "stitching": 20.00,
    "finishing": 18.00,
    "packing": 12.00,
}

OVERHEAD_RATE_PER_UNIT = 2.50 # $2.50 factory overhead per garment unit


class CostingService:

    @staticmethod
    async def create_standard_cost(
        db: AsyncSession, tenant_id: uuid.UUID, payload: StandardCostCreate
    ) -> StandardCost:
        std_total = payload.std_material_cost + payload.std_labor_cost + payload.std_overhead_cost
        cost = StandardCost(
            tenant_id=tenant_id,
            product_id=payload.product_id,
            component_id=payload.component_id,
            std_material_cost=payload.std_material_cost,
            std_labor_cost=payload.std_labor_cost,
            std_overhead_cost=payload.std_overhead_cost,
            std_total_cost=std_total,
        )
        db.add(cost)
        await db.commit()
        await db.refresh(cost)
        return cost

    @staticmethod
    async def list_standard_costs(db: AsyncSession) -> List[StandardCost]:
        res = await db.execute(select(StandardCost))
        return res.scalars().all()

    @staticmethod
    async def calculate_job_cost(
        db: AsyncSession, tenant_id: uuid.UUID, production_order_id: uuid.UUID
    ) -> JobCostSummaryResponse:
        po = await db.get(ProductionOrder, production_order_id)
        if not po:
            raise ValueError("Production Order not found.")

        target_qty = float(po.target_qty)

        # 1. Direct Material Cost: Explode BOM lines
        bom_res = await db.execute(
            select(BOMHeader).where(BOMHeader.product_id == po.product_id, BOMHeader.is_active == True)
        )
        bom = bom_res.scalar_one_or_none()
        material_cost_per_unit = 12.50 # Baseline component material cost per unit
        actual_mat_cost = target_qty * material_cost_per_unit

        # 2. Direct Labor Cost: Calculate work order lead times × stage labor rates
        actual_labor_cost = 0.0
        for wo in po.work_orders:
            rate = STAGE_LABOR_RATES.get(wo.stage.lower(), 15.00)
            actual_labor_cost += wo.lead_time_hours * rate

        # 3. Factory Overhead Cost
        actual_overhead_cost = target_qty * OVERHEAD_RATE_PER_UNIT

        actual_total = actual_mat_cost + actual_labor_cost + actual_overhead_cost

        # 4. Standard Cost target lookup
        std_res = await db.execute(
            select(StandardCost).where(StandardCost.product_id == po.product_id)
        )
        std_cost_rec = std_res.scalar_one_or_none()
        std_unit_total = float(std_cost_rec.std_total_cost) if std_cost_rec else 25.00
        std_total = std_unit_total * target_qty

        variance = round(actual_total - std_total, 2)
        is_favorable = variance <= 0

        # Save to JobCostLedger
        ledger = JobCostLedger(
            tenant_id=tenant_id,
            production_order_id=production_order_id,
            actual_material_cost=round(actual_mat_cost, 2),
            actual_labor_cost=round(actual_labor_cost, 2),
            actual_overhead_cost=round(actual_overhead_cost, 2),
            actual_total_cost=round(actual_total, 2),
            std_total_cost=round(std_total, 2),
            cost_variance=variance,
            is_favorable=is_favorable,
        )
        db.add(ledger)
        await db.commit()

        return JobCostSummaryResponse(
            production_order_id=production_order_id,
            product_id=po.product_id,
            target_qty=target_qty,
            actual_material_cost=round(actual_mat_cost, 2),
            actual_labor_cost=round(actual_labor_cost, 2),
            actual_overhead_cost=round(actual_overhead_cost, 2),
            actual_total_cost=round(actual_total, 2),
            std_total_cost=round(std_total, 2),
            cost_variance=variance,
            is_favorable=is_favorable,
            unit_cost_actual=round(actual_total / target_qty, 2) if target_qty > 0 else 0.0,
            unit_cost_standard=round(std_unit_total, 2),
        )
