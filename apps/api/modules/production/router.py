from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from typing import List
from datetime import datetime, timedelta, timezone
import uuid

from core.tenancy import get_tenant_db
from modules.auth.dependencies import get_current_user
from modules.auth.models import User
from modules.bom.models import Product, BOMHeader, BOMLine, Component
from modules.inventory.service import InventoryService
from modules.inventory.schemas import ReservationCreate, InventoryAdjustment
from modules.inventory.models import Inventory, InventoryReservation, StockMovement
from modules.sales.models import SalesOrder, SalesOrderLine
from modules.production.models import ProductionOrder, WorkOrder
from modules.production.schemas import ProductionOrderCreate, ProductionOrderResponse, GanttBarResponse

router = APIRouter(prefix="/production", tags=["Production Execution"])

# Stages in sequential order with their default lead times (hours)
STAGES = ["cutting", "stitching", "finishing", "packing"]
STAGE_LEAD_TIMES = {
    "cutting":   8,
    "stitching": 16,
    "finishing":  8,
    "packing":    4,
}

@router.post("/runs", response_model=ProductionOrderResponse, status_code=status.HTTP_201_CREATED)
async def schedule_production_run(
    run_in: ProductionOrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    # 1. Verify Product
    prod_exists = await db.execute(select(Product).where(Product.id == run_in.product_id))
    product = prod_exists.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    # 2. Get active BOM
    bom_res = await db.execute(
        select(BOMHeader)
        .options(selectinload(BOMHeader.lines))
        .where(BOMHeader.product_id == run_in.product_id, BOMHeader.is_active == True)
    )
    bom = bom_res.scalar_one_or_none()
    if not bom or not bom.lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active BOM required to schedule production run."
        )

    # 3. Explode BOM and check inventory availability
    components_needed = []
    for line in bom.lines:
        qty_needed = float(line.qty_per_unit) * float(run_in.target_qty) * (1.0 + float(line.scrap_pct) / 100.0)
        
        # Check stock balance
        stock = await InventoryService.get_inventory_balance(db, line.component_id, run_in.warehouse_id)
        available = stock.available_qty if stock else 0.00
        
        if available < qty_needed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient inventory for component ID {line.component_id}. Required: {qty_needed}, Available: {available}"
            )
        components_needed.append((line.component_id, qty_needed))

    # 4. Create Production Order
    po = ProductionOrder(
        tenant_id=current_user.tenant_id,
        org_id=current_user.org_id,
        product_id=run_in.product_id,
        sales_order_id=run_in.sales_order_id,
        target_qty=run_in.target_qty,
        status="scheduled"
    )
    db.add(po)
    await db.flush()

    # 5. Create Work Orders with chained scheduled dates derived from lead times
    stage_cursor = run_in.scheduled_start or datetime.now(timezone.utc)
    po.scheduled_start = stage_cursor

    for idx, stage in enumerate(STAGES):
        lead_h = STAGE_LEAD_TIMES[stage]
        wo_start = stage_cursor
        wo_end = stage_cursor + timedelta(hours=lead_h)
        wo = WorkOrder(
            tenant_id=current_user.tenant_id,
            production_order_id=po.id,
            stage=stage,
            sequence_no=idx + 1,
            status="pending",
            scheduled_start=wo_start,
            scheduled_end=wo_end,
            lead_time_hours=lead_h,
        )
        db.add(wo)
        stage_cursor = wo_end

    po.scheduled_end = stage_cursor  # end of the last stage

    # 6. Apply soft reservations for raw materials
    for comp_id, qty in components_needed:
        res_in = ReservationCreate(
            component_id=comp_id,
            warehouse_id=run_in.warehouse_id,
            quantity=qty,
            source_order_id=po.id
        )
        await InventoryService.create_reservation(db, res_in)

    await db.commit()

    # Reload PO with work orders
    res = await db.execute(
        select(ProductionOrder)
        .options(selectinload(ProductionOrder.work_orders))
        .where(ProductionOrder.id == po.id)
    )
    return res.scalar_one()

@router.get("/runs", response_model=List[ProductionOrderResponse])
async def list_production_runs(db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(
        select(ProductionOrder).options(selectinload(ProductionOrder.work_orders))
    )
    return result.scalars().all()

@router.post("/work-orders/{wo_id}/transition")
async def transition_work_order_stage(
    wo_id: uuid.UUID,
    target_status: str, # active, completed
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    if target_status not in ["active", "completed"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid target status.")

    # Fetch WorkOrder and eager load production_order details
    wo_res = await db.execute(
        select(WorkOrder)
        .options(selectinload(WorkOrder.production_order))
        .where(WorkOrder.id == wo_id)
    )
    wo = wo_res.scalar_one_or_none()
    if not wo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work Order not found.")

    po = wo.production_order

    now = datetime.now(timezone.utc)

    if target_status == "active":
        if wo.status != "pending":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Work Order must be pending to start.")
        wo.status = "active"
        wo.actual_start = now
        if po.status == "scheduled":
            po.status = "wip"
            po.actual_start = now

    elif target_status == "completed":
        if wo.status != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Work Order must be active to complete.")
        wo.status = "completed"
        wo.actual_end = now

        # Check if this was the final sequence stage (packing)
        if wo.sequence_no == 4:
            po.status = "completed"
            po.actual_end = now

            # 1. Resolve and consume reservations from stock
            res_query = await db.execute(
                select(InventoryReservation)
                .where(
                    InventoryReservation.source_order_id == po.id,
                    InventoryReservation.status == "active"
                )
            )
            reservations = res_query.scalars().all()

            for r in reservations:
                r.status = "completed"
                
                # Deduct inventory physical balances (decrement on_hand and decrement reserved)
                stock_res = await db.execute(
                    select(Inventory)
                    .where(Inventory.component_id == r.component_id, Inventory.warehouse_id == r.warehouse_id)
                    .with_for_update()
                )
                stock = stock_res.scalar_one()
                stock.on_hand_qty = max(0.00, float(stock.on_hand_qty) - float(r.quantity))
                stock.reserved_qty = max(0.00, float(stock.reserved_qty) - float(r.quantity))

                # Log issue movement to ledger
                movement = StockMovement(
                    tenant_id=r.tenant_id,
                    component_id=r.component_id,
                    warehouse_id=r.warehouse_id,
                    movement_type="adjustment", # Consumption issue
                    qty=-r.quantity,
                    reference_type="production_order",
                    reference_id=po.id,
                    created_by=current_user.id
                )
                db.add(movement)

            # 2. Update linked Sales Order Line production metrics
            if po.sales_order_id:
                so_line_res = await db.execute(
                    select(SalesOrderLine)
                    .where(
                        SalesOrderLine.sales_order_id == po.sales_order_id,
                        SalesOrderLine.product_id == po.product_id
                    )
                )
                so_line = so_line_res.scalar_one_or_none()
                if so_line:
                    so_line.qty_produced = float(so_line.qty_produced or 0.00) + float(po.target_qty)
                    
                    # Update overall sales order status if fully produced
                    so_res = await db.execute(
                        select(SalesOrder)
                        .options(selectinload(SalesOrder.lines))
                        .where(SalesOrder.id == po.sales_order_id)
                    )
                    so = so_res.scalar_one()
                    
                    # Check if all lines are completed
                    all_complete = True
                    for line in so.lines:
                        if float(line.qty_produced) < float(line.qty_ordered):
                            all_complete = False
                            break
                    so.status = "fulfilled" if all_complete else "partially_produced"

    await db.commit()
    return {"status": "success", "work_order_status": wo.status, "production_order_status": po.status}

@router.get("/schedule", response_model=List[GanttBarResponse])
async def get_production_schedule(db: AsyncSession = Depends(get_tenant_db)):
    """
    Returns all work orders as a flat list suitable for Gantt chart rendering.
    Sorted by production_order created_at then stage sequence_no.
    """
    result = await db.execute(
        select(WorkOrder)
        .options(selectinload(WorkOrder.production_order))
        .order_by(WorkOrder.production_order_id, WorkOrder.sequence_no)
    )
    work_orders = result.scalars().all()

    return [
        GanttBarResponse(
            production_order_id=wo.production_order_id,
            work_order_id=wo.id,
            stage=wo.stage,
            sequence_no=wo.sequence_no,
            status=wo.status,
            scheduled_start=wo.scheduled_start,
            scheduled_end=wo.scheduled_end,
            actual_start=wo.actual_start,
            actual_end=wo.actual_end,
            lead_time_hours=wo.lead_time_hours,
        )
        for wo in work_orders
    ]
