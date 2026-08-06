from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
import uuid

from core.tenancy import get_tenant_db
from modules.auth.dependencies import get_current_user
from modules.auth.models import User
from modules.purchasing.models import Supplier, PurchaseOrder, PurchaseOrderLine
from modules.purchasing.schemas import (
    SupplierCreate, SupplierResponse,
    POCreate, POResponse
)
from modules.inventory.service import InventoryService
from modules.inventory.schemas import InventoryAdjustment

router = APIRouter(prefix="/purchasing", tags=["Purchasing Lifecycle"])

# Suppliers
@router.post("/suppliers", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    sup_in: SupplierCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    # Check if supplier code exists
    exists = await db.execute(
        select(Supplier).where(
            Supplier.code == sup_in.code,
            Supplier.tenant_id == current_user.tenant_id
        )
    )
    if exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A supplier with this code already exists."
        )

    supplier = Supplier(
        tenant_id=current_user.tenant_id,
        org_id=current_user.org_id,
        code=sup_in.code,
        name=sup_in.name,
        contact_email=sup_in.contact_email
    )
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return supplier

@router.get("/suppliers", response_model=List[SupplierResponse])
async def list_suppliers(db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Supplier))
    return result.scalars().all()

# Purchase Orders
@router.post("/pos", response_model=POResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    po_in: POCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    # Verify supplier exists
    sup_exists = await db.execute(select(Supplier).where(Supplier.id == po_in.supplier_id))
    if not sup_exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found."
        )

    # Check PO number uniqueness
    po_exists = await db.execute(select(PurchaseOrder).where(PurchaseOrder.po_no == po_in.po_no))
    if po_exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A Purchase Order with this number already exists."
        )

    po = PurchaseOrder(
        tenant_id=current_user.tenant_id,
        org_id=current_user.org_id,
        supplier_id=po_in.supplier_id,
        po_no=po_in.po_no,
        status="draft"
    )
    db.add(po)
    await db.flush()

    for line in po_in.lines:
        po_line = PurchaseOrderLine(
            tenant_id=current_user.tenant_id,
            po_id=po.id,
            component_id=line.component_id,
            qty_ordered=line.qty_ordered,
            unit_cost=line.unit_cost
        )
        db.add(po_line)

    await db.commit()
    
    # Reload fully with lines
    res = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.lines))
        .where(PurchaseOrder.id == po.id)
    )
    return res.scalar_one()

@router.get("/pos", response_model=List[POResponse])
async def list_purchase_orders(db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.lines))
    )
    return result.scalars().all()

@router.post("/pos/{po_id}/approve", response_model=POResponse)
async def approve_purchase_order(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_db)
):
    result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.lines))
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Order not found.")

    if po.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve PO in status: {po.status}"
        )

    po.status = "ordered"
    await db.commit()
    return po

@router.post("/pos/{po_id}/receive", response_model=POResponse)
async def receive_purchase_order(
    po_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.lines))
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Order not found.")

    if po.status != "ordered":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot receive PO in status: {po.status} (Must be ordered)"
        )

    # Transition stock for each PO line
    for line in po.lines:
        adj = InventoryAdjustment(
            component_id=line.component_id,
            warehouse_id=warehouse_id,
            qty=line.qty_ordered,
            movement_type="grn"
        )
        await InventoryService.adjust_stock(db=db, adjustment=adj, user_id=current_user.id)

    po.status = "received"
    await db.commit()
    return po
