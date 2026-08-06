from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
import uuid

from core.tenancy import get_tenant_db
from modules.auth.dependencies import get_current_user
from modules.auth.models import User
from modules.bom.models import Warehouse, Product, Component, BOMHeader, BOMLine
from modules.bom.schemas import (
    WarehouseCreate, WarehouseResponse,
    ComponentCreate, ComponentResponse,
    ProductCreate, ProductResponse,
    BOMCreate, BOMResponse
)

router = APIRouter(tags=["Master Data & BOM"])

# Warehouses
@router.post("/warehouses", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    wh_in: WarehouseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    wh = Warehouse(
        tenant_id=current_user.tenant_id,
        org_id=current_user.org_id,
        code=wh_in.code,
        name=wh_in.name
    )
    db.add(wh)
    await db.commit()
    await db.refresh(wh)
    return wh

@router.get("/warehouses", response_model=List[WarehouseResponse])
async def list_warehouses(db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Warehouse))
    return result.scalars().all()

# Components
@router.post("/components", response_model=ComponentResponse, status_code=status.HTTP_201_CREATED)
async def create_component(
    comp_in: ComponentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    # Check uniqueness of code
    check_exists = await db.execute(
        select(Component).where(
            Component.code == comp_in.code,
            Component.tenant_id == current_user.tenant_id
        )
    )
    if check_exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A component with this code already exists."
        )
        
    comp = Component(
        tenant_id=current_user.tenant_id,
        org_id=current_user.org_id,
        code=comp_in.code,
        name=comp_in.name,
        uom=comp_in.uom,
        reorder_level=comp_in.reorder_level,
        safety_stock=comp_in.safety_stock
    )
    db.add(comp)
    await db.commit()
    await db.refresh(comp)
    return comp

@router.get("/components", response_model=List[ComponentResponse])
async def list_components(db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Component))
    return result.scalars().all()

# Products
@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    prod_in: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    # Check uniqueness of SKU
    check_exists = await db.execute(
        select(Product).where(
            Product.sku == prod_in.sku,
            Product.tenant_id == current_user.tenant_id
        )
    )
    if check_exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A product with this SKU already exists."
        )

    prod = Product(
        tenant_id=current_user.tenant_id,
        org_id=current_user.org_id,
        sku=prod_in.sku,
        name=prod_in.name,
        category=prod_in.category
    )
    db.add(prod)
    await db.commit()
    await db.refresh(prod)
    return prod

@router.get("/products", response_model=List[ProductResponse])
async def list_products(db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Product))
    return result.scalars().all()

# BOM Creation
@router.post("/products/{product_id}/boms", response_model=BOMResponse, status_code=status.HTTP_201_CREATED)
async def create_bom(
    product_id: uuid.UUID,
    bom_in: BOMCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db)
):
    # Verify product exists
    product_exists = await db.execute(select(Product).where(Product.id == product_id))
    if not product_exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
        
    # Deactivate previous active BOMs if setting this to active
    if bom_in.is_active:
        await db.execute(
            BOMHeader.__table__.update()
            .where(BOMHeader.product_id == product_id)
            .values(is_active=False)
        )

    # Create BOM Header
    bom_header = BOMHeader(
        tenant_id=current_user.tenant_id,
        product_id=product_id,
        version=bom_in.version,
        is_active=bom_in.is_active
    )
    db.add(bom_header)
    await db.flush()

    # Create BOM Lines
    for line in bom_in.lines:
        bom_line = BOMLine(
            tenant_id=current_user.tenant_id,
            bom_header_id=bom_header.id,
            component_id=line.component_id,
            qty_per_unit=line.qty_per_unit,
            scrap_pct=line.scrap_pct
        )
        db.add(bom_line)

        
    await db.commit()
    
    # Reload with components
    result = await db.execute(
        select(BOMHeader)
        .options(
            selectinload(BOMHeader.lines).selectinload(BOMLine.component)
        )
        .where(BOMHeader.id == bom_header.id)
    )
    return result.scalar_one()

@router.get("/boms/{bom_id}", response_model=BOMResponse)
async def get_bom(
    bom_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_db)
):
    result = await db.execute(
        select(BOMHeader)
        .options(
            selectinload(BOMHeader.lines).selectinload(BOMLine.component)
        )
        .where(BOMHeader.id == bom_id)
    )
    bom = result.scalar_one_or_none()
    if not bom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BOM not found"
        )
    return bom
