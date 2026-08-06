from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import uuid

from core.tenancy import get_tenant_db
from modules.auth.dependencies import get_current_user
from modules.auth.models import User
from modules.inventory.schemas import InventoryResponse, InventoryAdjustment, ReservationCreate, ReservationResponse, InventoryTransferCreate
from modules.inventory.service import InventoryService
from modules.inventory.models import Inventory, InventoryReservation

router = APIRouter(prefix="/inventory", tags=["Inventory Management"])

@router.get("/balances", response_model=List[InventoryResponse])
async def list_balances(
    warehouse_id: Optional[uuid.UUID] = None,
    component_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_tenant_db)
):
    query = select(Inventory)
    if warehouse_id:
        query = query.where(Inventory.warehouse_id == warehouse_id)
    if component_id:
        query = query.where(Inventory.component_id == component_id)
        
    result = await db.execute(query)
    balances = result.scalars().all()
    return balances

@router.post("/adjustments", response_model=InventoryResponse)
async def adjust_stock(
    adjustment: InventoryAdjustment,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    try:
        updated_stock = await InventoryService.adjust_stock(
            db=db,
            adjustment=adjustment,
            user_id=current_user.id
        )
        await db.commit()
        return updated_stock
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/reservations", response_model=ReservationResponse)
async def create_reservation(
    reservation: ReservationCreate,
    db: AsyncSession = Depends(get_tenant_db)
):
    try:
        res = await InventoryService.create_reservation(db=db, res_in=reservation)
        await db.commit()
        return res
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/transfers", response_model=List[InventoryResponse])
async def transfer_stock(
    transfer: InventoryTransferCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    try:
        updated_stocks = await InventoryService.transfer_stock(
            db=db,
            from_warehouse_id=transfer.from_warehouse_id,
            to_warehouse_id=transfer.to_warehouse_id,
            component_id=transfer.component_id,
            qty=transfer.qty,
            user_id=current_user.id
        )
        await db.commit()
        return updated_stocks
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/reservations/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def release_reservation(
    reservation_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_db)
):
    try:
        await InventoryService.release_reservation(db=db, reservation_id=reservation_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
