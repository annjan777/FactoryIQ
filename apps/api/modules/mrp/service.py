"""
MRP (Material Requirements Planning) Engine

Algorithm:
  1. Load all open sales order lines (status not in fulfilled, cancelled)
  2. Explode BOM for each product × qty_ordered
  3. Aggregate gross requirements per component
  4. Subtract available inventory from each component
  5. For net shortfalls, find preferred supplier per component
  6. Group shortfalls by supplier → create draft PurchaseOrders + lines
"""
import uuid
from collections import defaultdict
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import text

from modules.sales.models import SalesOrder, SalesOrderLine
from modules.bom.models import BOMHeader, BOMLine, Component
from modules.inventory.models import Inventory
from modules.purchasing.models import Supplier, PurchaseOrder, PurchaseOrderLine, SupplierComponent
from modules.mrp.schemas import MRPRunResult, MRPRequirementLine, MRPDraftPO


class MRPService:

    @staticmethod
    async def run(
        db: AsyncSession,
        warehouse_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> MRPRunResult:
        # ── 1. Resolve tenant ────────────────────────────────────────────
        ctx = await db.execute(text("SELECT current_setting('app.current_tenant', true)"))
        tenant_id_str = ctx.scalar()
        if not tenant_id_str:
            raise ValueError("Tenant context not initialized")
        tenant_id = uuid.UUID(tenant_id_str)

        # ── 2. Fetch all open sales order lines ──────────────────────────
        so_res = await db.execute(
            select(SalesOrder)
            .options(selectinload(SalesOrder.lines))
            .where(SalesOrder.status.notin_(["fulfilled", "cancelled"]))
        )
        open_orders = so_res.scalars().all()

        # ── 3. BOM explosion → gross_requirements[component_id] ──────────
        gross: Dict[uuid.UUID, float] = defaultdict(float)

        for so in open_orders:
            for line in so.lines:
                remaining = float(line.qty_ordered) - float(line.qty_produced or 0)
                if remaining <= 0:
                    continue

                bom_res = await db.execute(
                    select(BOMHeader)
                    .options(selectinload(BOMHeader.lines))
                    .where(
                        BOMHeader.product_id == line.product_id,
                        BOMHeader.is_active == True
                    )
                )
                bom = bom_res.scalar_one_or_none()
                if not bom:
                    continue

                for bom_line in bom.lines:
                    qty_needed = remaining * float(bom_line.qty_per_unit) * (
                        1.0 + float(bom_line.scrap_pct) / 100.0
                    )
                    gross[bom_line.component_id] += qty_needed

        # ── 4. Fetch available inventory for each component ───────────────
        inv_res = await db.execute(
            select(Inventory).where(Inventory.warehouse_id == warehouse_id)
        )
        inventory_map: Dict[uuid.UUID, float] = {
            row.component_id: row.available_qty
            for row in inv_res.scalars().all()
        }

        # ── 5. Fetch all components metadata ─────────────────────────────
        comp_ids = list(gross.keys())
        comp_res = await db.execute(
            select(Component).where(Component.id.in_(comp_ids))
        )
        components = {c.id: c for c in comp_res.scalars().all()}

        # ── 6. Fetch preferred supplier mappings ─────────────────────────
        sc_res = await db.execute(
            select(SupplierComponent)
            .options(selectinload(SupplierComponent.supplier))
            .where(
                SupplierComponent.component_id.in_(comp_ids),
                SupplierComponent.is_preferred == True
            )
        )
        supplier_map: Dict[uuid.UUID, SupplierComponent] = {
            sc.component_id: sc for sc in sc_res.scalars().all()
        }

        # ── 7. Compute requirements lines and group shortfalls ────────────
        requirements: List[MRPRequirementLine] = []
        # shortfalls_by_supplier[supplier_id] = [(component_id, qty, unit_cost)]
        shortfalls_by_supplier: Dict[uuid.UUID, list] = defaultdict(list)

        for comp_id, gross_qty in gross.items():
            available = inventory_map.get(comp_id, 0.0)
            net = max(0.0, gross_qty - available)
            comp = components.get(comp_id)
            sc = supplier_map.get(comp_id)

            req = MRPRequirementLine(
                component_id=comp_id,
                component_code=comp.code if comp else str(comp_id),
                component_name=comp.name if comp else "Unknown",
                gross_requirement=round(gross_qty, 4),
                available_qty=round(available, 4),
                net_requirement=round(net, 4),
                shortfall=net > 0,
                preferred_supplier_id=sc.supplier_id if sc else None,
                preferred_supplier_name=sc.supplier.name if sc else None,
                unit_cost=float(sc.unit_cost) if sc else None,
                lead_time_days=sc.lead_time_days if sc else None,
            )
            requirements.append(req)

            if net > 0 and sc:
                shortfalls_by_supplier[sc.supplier_id].append(
                    (comp_id, net, float(sc.unit_cost))
                )

        # ── 8. Generate draft POs per supplier ────────────────────────────
        draft_pos: List[MRPDraftPO] = []
        po_seq = 1

        for supplier_id, lines in shortfalls_by_supplier.items():
            # Fetch supplier name
            sup_res = await db.execute(
                select(Supplier).where(Supplier.id == supplier_id)
            )
            supplier = sup_res.scalar_one_or_none()
            if not supplier:
                continue

            po_no = f"MRP-{str(tenant_id)[:8].upper()}-{po_seq:04d}"
            po_seq += 1

            po = PurchaseOrder(
                tenant_id=tenant_id,
                org_id=supplier.org_id,
                supplier_id=supplier_id,
                po_no=po_no,
                status="draft",
            )
            db.add(po)
            await db.flush()

            total_cost = 0.0
            for comp_id, qty, unit_cost in lines:
                line_cost = qty * unit_cost
                total_cost += line_cost
                po_line = PurchaseOrderLine(
                    tenant_id=tenant_id,
                    po_id=po.id,
                    component_id=comp_id,
                    qty_ordered=round(qty, 4),
                    unit_cost=unit_cost,
                )
                db.add(po_line)

            draft_pos.append(MRPDraftPO(
                po_id=po.id,
                po_no=po_no,
                supplier_id=supplier_id,
                supplier_name=supplier.name,
                line_count=len(lines),
                total_cost=round(total_cost, 2),
            ))

        await db.flush()

        return MRPRunResult(
            warehouse_id=warehouse_id,
            total_components_analysed=len(requirements),
            shortfall_count=sum(1 for r in requirements if r.shortfall),
            draft_pos_created=draft_pos,
            requirements=requirements,
        )
