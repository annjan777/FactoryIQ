from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from core.tenancy import get_tenant_db
from modules.auth.dependencies import get_current_user
from modules.auth.models import User
from modules.quality.schemas import (
    InspectionGateCreate,
    InspectionGateResponse,
    QualityInspectionCreate,
    QualityInspectionResponse,
)
from modules.quality.service import QualityService

router = APIRouter(prefix="/quality", tags=["Quality Control & Inspection Gates"])


@router.get("/gates", response_model=List[InspectionGateResponse])
async def list_inspection_gates(
    db: AsyncSession = Depends(get_tenant_db),
    _: User = Depends(get_current_user),
):
    """List active quality inspection gates for the current tenant."""
    return await QualityService.list_gates(db)


@router.post("/gates", response_model=InspectionGateResponse, status_code=status.HTTP_201_CREATED)
async def create_inspection_gate(
    payload: InspectionGateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Define a quality inspection gate rule for a stage."""
    return await QualityService.create_gate(db, current_user.tenant_id, payload)


@router.get("/inspections", response_model=List[QualityInspectionResponse])
async def list_inspections(
    db: AsyncSession = Depends(get_tenant_db),
    _: User = Depends(get_current_user),
):
    """List quality inspection history logs."""
    return await QualityService.list_inspections(db)


@router.post("/inspections", response_model=QualityInspectionResponse, status_code=status.HTTP_201_CREATED)
async def record_inspection(
    payload: QualityInspectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Record a quality inspection check against a Work Order or PO Line."""
    try:
        return await QualityService.record_inspection(
            db, current_user.tenant_id, current_user.id, payload
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
