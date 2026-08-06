"""
Unit tests for MRP (Material Requirements Planning) Engine:
- Verifies BOM explosion accumulates gross component requirements from open Sales Orders.
- Verifies net requirement calculation: net = max(0, gross - available_inventory).
- Verifies draft PO creation groups shortfalls by preferred supplier.
- Verifies components with sufficient inventory create no draft PO lines.
"""
import pytest
import uuid
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Component:
    id: uuid.UUID
    code: str
    name: str

@dataclass
class BOMLine:
    component_id: uuid.UUID
    qty_per_unit: float
    scrap_pct: float = 0.0

@dataclass
class SalesOrderLine:
    product_id: uuid.UUID
    qty_ordered: float
    qty_produced: float = 0.0

@dataclass
class SupplierComponent:
    component_id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: str
    unit_cost: float
    lead_time_days: int
    is_preferred: bool = True


# Simulated pure unit-test engine function matching MRPService logic
def calculate_mrp_requirements(
    so_lines: List[SalesOrderLine],
    boms: Dict[uuid.UUID, List[BOMLine]],
    inventory: Dict[uuid.UUID, float],
    components: Dict[uuid.UUID, Component],
    supplier_map: Dict[uuid.UUID, SupplierComponent],
):
    # 1. Gross requirements
    gross: Dict[uuid.UUID, float] = {}
    for line in so_lines:
        remaining = line.qty_ordered - line.qty_produced
        if remaining <= 0:
            continue
        lines = boms.get(line.product_id, [])
        for bl in lines:
            qty_needed = remaining * bl.qty_per_unit * (1.0 + bl.scrap_pct / 100.0)
            gross[bl.component_id] = gross.get(bl.component_id, 0.0) + qty_needed

    # 2. Net requirements & PO grouping
    requirements = []
    draft_pos_by_supplier = {}

    for comp_id, gross_qty in gross.items():
        avail = inventory.get(comp_id, 0.0)
        net = max(0.0, gross_qty - avail)
        comp = components.get(comp_id)
        sc = supplier_map.get(comp_id)

        req = {
            "component_id": comp_id,
            "component_code": comp.code if comp else str(comp_id),
            "gross_requirement": round(gross_qty, 4),
            "available_qty": round(avail, 4),
            "net_requirement": round(net, 4),
            "shortfall": net > 0,
            "preferred_supplier_id": sc.supplier_id if sc else None,
            "unit_cost": sc.unit_cost if sc else None,
        }
        requirements.append(req)

        if net > 0 and sc:
            if sc.supplier_id not in draft_pos_by_supplier:
                draft_pos_by_supplier[sc.supplier_id] = {
                    "supplier_name": sc.supplier_name,
                    "lines": [],
                    "total_cost": 0.0,
                }
            line_cost = net * sc.unit_cost
            draft_pos_by_supplier[sc.supplier_id]["lines"].append((comp_id, net, sc.unit_cost))
            draft_pos_by_supplier[sc.supplier_id]["total_cost"] += line_cost

    return requirements, draft_pos_by_supplier


class TestMRPEngineLogic:

    def test_bom_explosion_accumulates_gross_requirements(self):
        comp_a = uuid.uuid4()
        comp_b = uuid.uuid4()
        prod_1 = uuid.uuid4()

        boms = {
            prod_1: [
                BOMLine(component_id=comp_a, qty_per_unit=2.0, scrap_pct=10.0), # 2.0 * 1.1 = 2.2 per unit
                BOMLine(component_id=comp_b, qty_per_unit=5.0, scrap_pct=0.0),  # 5.0 per unit
            ]
        }

        so_lines = [
            SalesOrderLine(product_id=prod_1, qty_ordered=100.0, qty_produced=20.0), # remaining 80
        ]

        components = {
            comp_a: Component(id=comp_a, code="COMP-A", name="Steel Plate"),
            comp_b: Component(id=comp_b, code="COMP-B", name="Bolts"),
        }

        inventory = {
            comp_a: 50.0, # Gross 80 * 2.2 = 176.0 -> Net 176 - 50 = 126.0
            comp_b: 500.0, # Gross 80 * 5 = 400.0 -> Net 400 - 500 = 0 (Surplus)
        }

        sup_id = uuid.uuid4()
        supplier_map = {
            comp_a: SupplierComponent(
                component_id=comp_a, supplier_id=sup_id, supplier_name="FastenerCo", unit_cost=12.50, lead_time_days=5
            )
        }

        reqs, draft_pos = calculate_mrp_requirements(
            so_lines=so_lines,
            boms=boms,
            inventory=inventory,
            components=components,
            supplier_map=supplier_map,
        )

        req_a = next(r for r in reqs if r["component_id"] == comp_a)
        assert req_a["gross_requirement"] == 176.0
        assert req_a["available_qty"] == 50.0
        assert req_a["net_requirement"] == 126.0
        assert req_a["shortfall"] is True

        req_b = next(r for r in reqs if r["component_id"] == comp_b)
        assert req_b["gross_requirement"] == 400.0
        assert req_b["available_qty"] == 500.0
        assert req_b["net_requirement"] == 0.0
        assert req_b["shortfall"] is False

        # Verify draft PO created ONLY for shortfall comp_a
        assert sup_id in draft_pos
        po = draft_pos[sup_id]
        assert len(po["lines"]) == 1
        assert po["lines"][0] == (comp_a, 126.0, 12.50)
        assert po["total_cost"] == 126.0 * 12.50

    def test_zero_remaining_sales_orders_skipped(self):
        comp_a = uuid.uuid4()
        prod_1 = uuid.uuid4()

        boms = {prod_1: [BOMLine(component_id=comp_a, qty_per_unit=1.0)]}
        so_lines = [SalesOrderLine(product_id=prod_1, qty_ordered=50.0, qty_produced=50.0)]
        components = {comp_a: Component(id=comp_a, code="COMP-A", name="Plate")}

        reqs, draft_pos = calculate_mrp_requirements(
            so_lines=so_lines, boms=boms, inventory={}, components=components, supplier_map={}
        )

        assert len(reqs) == 0
        assert len(draft_pos) == 0

    def test_draft_pos_grouped_by_supplier(self):
        comp_a = uuid.uuid4()
        comp_b = uuid.uuid4()
        prod_1 = uuid.uuid4()

        sup_1 = uuid.uuid4()
        sup_2 = uuid.uuid4()

        boms = {
            prod_1: [
                BOMLine(component_id=comp_a, qty_per_unit=1.0),
                BOMLine(component_id=comp_b, qty_per_unit=2.0),
            ]
        }
        so_lines = [SalesOrderLine(product_id=prod_1, qty_ordered=10.0)]
        components = {
            comp_a: Component(id=comp_a, code="COMP-A", name="Part A"),
            comp_b: Component(id=comp_b, code="COMP-B", name="Part B"),
        }
        supplier_map = {
            comp_a: SupplierComponent(component_id=comp_a, supplier_id=sup_1, supplier_name="Supplier 1", unit_cost=10.0, lead_time_days=3),
            comp_b: SupplierComponent(component_id=comp_b, supplier_id=sup_2, supplier_name="Supplier 2", unit_cost=20.0, lead_time_days=7),
        }

        reqs, draft_pos = calculate_mrp_requirements(
            so_lines=so_lines, boms=boms, inventory={}, components=components, supplier_map=supplier_map
        )

        assert len(draft_pos) == 2
        assert sup_1 in draft_pos
        assert sup_2 in draft_pos
