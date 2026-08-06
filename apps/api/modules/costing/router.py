from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from core.tenancy import get_tenant_db
from modules.auth.dependencies import get_current_user
from modules.auth.models import User
from modules.costing.schemas import (
    StandardCostCreate,
    StandardCostResponse,
    JobCostSummaryResponse,
)
from modules.costing.service import CostingService

router = APIRouter(prefix="/costing", tags=["Product Costing & Job Ledger"])


@router.get("/standard-costs", response_model=List[StandardCostResponse])
async def list_standard_costs(
    db: AsyncSession = Depends(get_tenant_db),
    _: User = Depends(get_current_user),
):
    """List standard cost benchmarks for products and components."""
    return await CostingService.list_standard_costs(db)


@router.post("/standard-costs", response_model=StandardCostResponse, status_code=status.HTTP_201_CREATED)
async def create_standard_cost(
    payload: StandardCostCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Define standard material, labor, and overhead target costs."""
    return await CostingService.create_standard_cost(db, current_user.tenant_id, payload)


@router.get("/job-cost/{production_order_id}", response_model=JobCostSummaryResponse)
async def calculate_job_cost(
    production_order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Calculate actual job costing vs standard cost targets with variance analysis."""
    try:
        return await CostingService.calculate_job_cost(
            db, current_user.tenant_id, production_order_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
