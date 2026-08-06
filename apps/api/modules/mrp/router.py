from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
import uuid

from core.tenancy import get_tenant_db
from modules.auth.dependencies import get_current_user
from modules.auth.models import User
from modules.purchasing.models import SupplierComponent, Supplier
from modules.bom.models import Component
from modules.mrp.schemas import (
    MRPRunResult,
    SupplierComponentCreate,
    SupplierComponentResponse,
)
from modules.mrp.service import MRPService

router = APIRouter(prefix="/mrp", tags=["MRP Engine"])


@router.post("/run", response_model=MRPRunResult)
async def run_mrp(
    warehouse_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    Run the MRP engine for a given warehouse.

    Steps performed:
      1. Explode BOMs for all open sales orders
      2. Compute net requirements (gross − available stock)
      3. Auto-create draft Purchase Orders for shortfalls grouped by supplier

    Returns the full requirements list and a summary of draft POs created.
    """
    try:
        result = await MRPService.run(
            db=db,
            warehouse_id=warehouse_id,
            user_id=current_user.id,
        )
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/supplier-components", response_model=List[SupplierComponentResponse])
async def list_supplier_components(
    db: AsyncSession = Depends(get_tenant_db),
    _: User = Depends(get_current_user),
):
    """List all component–supplier mappings for the current tenant."""
    res = await db.execute(
        select(SupplierComponent)
        .options(
            selectinload(SupplierComponent.supplier),
            selectinload(SupplierComponent.component),
        )
    )
    return res.scalars().all()


@router.post(
    "/supplier-components",
    response_model=SupplierComponentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_supplier_component(
    payload: SupplierComponentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Register a supplier as a source for a component."""
    # Validate supplier exists
    sup = await db.get(Supplier, payload.supplier_id)
    if not sup:
        raise HTTPException(status_code=404, detail="Supplier not found.")

    # Validate component exists
    comp = await db.get(Component, payload.component_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Component not found.")

    # If marking preferred, unmark any existing preferred for this component
    if payload.is_preferred:
        existing_res = await db.execute(
            select(SupplierComponent).where(
                SupplierComponent.component_id == payload.component_id,
                SupplierComponent.is_preferred == True,
            )
        )
        for sc in existing_res.scalars().all():
            sc.is_preferred = False

    sc = SupplierComponent(
        tenant_id=current_user.tenant_id,
        supplier_id=payload.supplier_id,
        component_id=payload.component_id,
        unit_cost=payload.unit_cost,
        lead_time_days=payload.lead_time_days,
        is_preferred=payload.is_preferred,
    )
    db.add(sc)
    await db.commit()
    await db.refresh(sc)
    return sc
