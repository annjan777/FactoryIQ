import uuid
import math
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from modules.sales.models import SalesOrder, SalesOrderLine
from modules.sales.schemas import FeasibilityResponse, FeasibilityComponentResult, PurchaseOrderSuggestion
from modules.bom.models import BOMHeader, BOMLine, Component
from modules.inventory.models import Inventory

class FeasibilityService:
    @staticmethod
    async def evaluate_order(
        db: AsyncSession,
        sales_order_id: uuid.UUID
    ) -> FeasibilityResponse:
        """
        Runs the deterministic BOM explosion and MRP checks for a Sales Order.
        Aggregates available stock across all warehouses, subtracts soft/hard holds,
        identifies limiting components, and returns procurement suggestions.
        """
        # 1. Fetch Sales Order
        result = await db.execute(
            select(SalesOrder)
            .options(selectinload(SalesOrder.lines))
            .where(SalesOrder.id == sales_order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise ValueError("Sales Order not found")

        # Track aggregated requirements and balances
        requested_qty = 0.0
        component_requirements: Dict[uuid.UUID, Dict] = {} # component_id -> {qty_per_unit, required_total, component_obj}
        
        # 2. Iterate through order lines (e.g. products ordered)
        for line in order.lines:
            requested_qty += float(line.qty_ordered)
            
            # Fetch active BOM for product
            bom_result = await db.execute(
                select(BOMHeader)
                .options(selectinload(BOMHeader.lines).selectinload(BOMLine.component))
                .where(BOMHeader.product_id == line.product_id, BOMHeader.is_active == True)
            )
            bom = bom_result.scalar_one_or_none()
            if not bom:
                raise ValueError(f"No active Bill of Materials found for Product UUID: {line.product_id}")

            # Explode BOM and aggregate raw material demand
            for bom_line in bom.lines:
                comp_id = bom_line.component_id
                comp = bom_line.component
                
                # scrap_pct yield calculation: total_needed = qty_per * order_qty * (1 + scrap_pct/100)
                qty_needed_per_garment = float(bom_line.qty_per_unit) * (1.0 + float(bom_line.scrap_pct) / 100.0)
                line_required = qty_needed_per_garment * float(line.qty_ordered)
                
                if comp_id not in component_requirements:
                    component_requirements[comp_id] = {
                        "qty_per_unit": float(bom_line.qty_per_unit),
                        "required_total": 0.0,
                        "component": comp
                    }
                component_requirements[comp_id]["required_total"] += line_required

        if not component_requirements:
            raise ValueError("Sales order contains no product lines or valid BOM components")

        # 3. Retrieve inventory balances across all warehouses for required components
        comp_ids = list(component_requirements.keys())
        inventory_result = await db.execute(
            select(Inventory).where(Inventory.component_id.in_(comp_ids))
        )
        inventory_list = inventory_result.scalars().all()
        
        # Aggregate available stock by component
        # available_qty = on_hand_qty - reserved_qty - allocated_qty - damaged_qty
        component_available: Dict[uuid.UUID, float] = {cid: 0.0 for cid in comp_ids}
        for inv in inventory_list:
            component_available[inv.component_id] += inv.available_qty

        # 4. Perform the mathematical availability check
        max_producible_by_component: Dict[uuid.UUID, float] = {}
        limiting_comp_details: List[FeasibilityComponentResult] = []
        po_suggestions: List[PurchaseOrderSuggestion] = []
        
        for cid, req in component_requirements.items():
            comp_obj = req["component"]
            required_total = req["required_total"]
            qty_per_unit = req["qty_per_unit"]
            available = component_available[cid]
            
            # calculate limits
            if qty_per_unit > 0:
                max_producible_by_component[cid] = math.floor(available / qty_per_unit)
            else:
                max_producible_by_component[cid] = float('inf')
                
            # calculate shortage and recommendations
            shortfall = max(0.0, required_total - available)
            if shortfall > 0:
                po_suggestions.append(
                    PurchaseOrderSuggestion(
                        component_id=cid,
                        component_code=comp_obj.code,
                        qty=shortfall
                    )
                )
                
        # Producible quantity is limited by the component with the minimum capacity
        if max_producible_by_component:
            producible_qty = min(max_producible_by_component.values())
        else:
            producible_qty = 0.0
            
        shortfall_qty = max(0.0, requested_qty - producible_qty)
        readiness_pct = round((producible_qty / requested_qty) * 100.0, 2) if requested_qty > 0 else 100.0

        # Identify bottleneck components causing the limit
        for cid, prod_limit in max_producible_by_component.items():
            if prod_limit == producible_qty and shortfall_qty > 0:
                comp_obj = component_requirements[cid]["component"]
                required_total = component_requirements[cid]["required_total"]
                available = component_available[cid]
                shortfall = max(0.0, required_total - available)
                
                limiting_comp_details.append(
                    FeasibilityComponentResult(
                        component_id=cid,
                        component_name=comp_obj.name,
                        component_code=comp_obj.code,
                        available_qty=available,
                        required_qty=required_total,
                        shortfall_qty=shortfall
                    )
                )

        return FeasibilityResponse(
            sales_order_id=sales_order_id,
            requested_qty=requested_qty,
            producible_qty=producible_qty,
            shortfall_qty=shortfall_qty,
            limiting_components=limiting_comp_details,
            readiness_pct=readiness_pct,
            recommended_purchase_orders=po_suggestions
        )
