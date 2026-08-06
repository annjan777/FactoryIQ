from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
import uuid

from core.tenancy import get_tenant_db
from modules.auth.dependencies import get_current_user
from modules.auth.models import User
from modules.sales.models import SalesOrder, SalesOrderLine
from modules.sales.schemas import SalesOrderCreate, SalesOrderResponse, FeasibilityResponse
from modules.sales.service import FeasibilityService

router = APIRouter(tags=["Sales & Order Feasibility"])

@router.post("/sales-orders", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_sales_order(
    so_in: SalesOrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    # Verify order number unique for tenant
    check_exists = await db.execute(
        select(SalesOrder).where(
            SalesOrder.order_no == so_in.order_no,
            SalesOrder.tenant_id == current_user.tenant_id
        )
    )
    if check_exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A sales order with this order number already exists."
        )

    # 1. Create Sales Order Header
    so = SalesOrder(
        tenant_id=current_user.tenant_id,
        order_no=so_in.order_no,
        customer_id=so_in.customer_id,
        status="open"
    )
    db.add(so)
    await db.flush()

    # 2. Create Sales Order Lines
    for line in so_in.lines:
        so_line = SalesOrderLine(
            tenant_id=current_user.tenant_id,
            sales_order_id=so.id,
            product_id=line.product_id,
            qty_ordered=line.qty_ordered
        )
        db.add(so_line)

        
    await db.commit()
    
    # Reload with lines
    result = await db.execute(
        select(SalesOrder)
        .options(selectinload(SalesOrder.lines))
        .where(SalesOrder.id == so.id)
    )
    return result.scalar_one()

@router.get("/sales-orders", response_model=List[SalesOrderResponse])
async def list_sales_orders(db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(
        select(SalesOrder).options(selectinload(SalesOrder.lines))
    )
    return result.scalars().all()

@router.get("/sales-orders/{sales_order_id}", response_model=SalesOrderResponse)
async def get_sales_order(
    sales_order_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_db)
):
    result = await db.execute(
        select(SalesOrder)
        .options(selectinload(SalesOrder.lines))
        .where(SalesOrder.id == sales_order_id)
    )
    so = result.scalar_one_or_none()
    if not so:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales Order not found"
        )
    return so

@router.get("/sales-orders/{sales_order_id}/feasibility", response_model=FeasibilityResponse)
async def check_order_feasibility(
    sales_order_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_db)
):
    try:
        feasibility = await FeasibilityService.evaluate_order(db=db, sales_order_id=sales_order_id)
        return feasibility
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
