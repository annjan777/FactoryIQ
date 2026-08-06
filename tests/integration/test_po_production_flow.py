import pytest
import pytest_asyncio
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text, select
from sqlalchemy.orm import selectinload

from db.session import Base
from modules.auth.models import Tenant, Organization, User
from modules.bom.models import Warehouse, Product, Component, BOMHeader, BOMLine
from modules.inventory.models import Inventory, InventoryReservation, StockMovement
from modules.inventory.service import InventoryService
from modules.inventory.schemas import InventoryAdjustment, ReservationCreate
from modules.sales.models import SalesOrder, SalesOrderLine
from modules.purchasing.models import Supplier, PurchaseOrder, PurchaseOrderLine
from modules.production.models import ProductionOrder, WorkOrder

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import ARRAY

@compiles(ARRAY, 'sqlite')
def compile_array_sqlite(element, compiler, **kw):
    return "TEXT"

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    from sqlalchemy import event
    @event.listens_for(engine.sync_engine, "connect")
    def register_sqlite_stubs(dbapi_connection, connection_record):
        def set_config(name, val, is_local):
            connection_record.info[name] = val
            return val
            
        def current_setting(name, is_local=True):
            return connection_record.info.get(name)
            
        dbapi_connection.create_function("set_config", 3, set_config)
        dbapi_connection.create_function("current_setting", 2, current_setting)
        
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
        
    await engine.dispose()

@pytest.mark.asyncio
async def test_purchasing_and_production_execution_flow(db_session: AsyncSession):
    # 1. Setup tenant & org contexts
    tenant_id = uuid.uuid4()
    org_id = uuid.uuid4()
    
    tenant = Tenant(id=tenant_id, name="GarmentCorp", subdomain="garment", plan="standard")
    org = Organization(id=org_id, tenant_id=tenant_id, name="HQ Warehouse", industry="garment")
    user = User(id=uuid.uuid4(), tenant_id=tenant_id, org_id=org_id, email="manager@garment.com", password_hash="hash", status="active")
    
    db_session.add_all([tenant, org, user])
    await db_session.flush()

    # Seed local connection parameters (mock RLS context)
    await db_session.execute(
        text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
        {"tenant_id": str(tenant_id)}
    )

    # 2. Setup Warehouse & Supplier
    warehouse = Warehouse(tenant_id=tenant_id, org_id=org_id, code="WH-1", name="Main Warehouse")
    supplier = Supplier(tenant_id=tenant_id, org_id=org_id, code="SUPP-01", name="Thread & Panel Co.")
    db_session.add_all([warehouse, supplier])
    await db_session.flush()

    # 3. Create Product (T-Shirt) & 5 Components
    product = Product(id=uuid.uuid4(), tenant_id=tenant_id, org_id=org_id, sku="TSHIRT-RN-101", name="Round Neck T-Shirt")
    db_session.add(product)
    
    comp_front = Component(tenant_id=tenant_id, org_id=org_id, code="FRONT-PANEL", name="Front Panel", uom="pcs")
    comp_back = Component(tenant_id=tenant_id, org_id=org_id, code="BACK-PANEL", name="Back Panel", uom="pcs")
    comp_sleeve = Component(tenant_id=tenant_id, org_id=org_id, code="SLEEVE", name="Sleeve Pair", uom="pcs")
    comp_collar = Component(tenant_id=tenant_id, org_id=org_id, code="COLLAR", name="Collar", uom="pcs")
    comp_label = Component(tenant_id=tenant_id, org_id=org_id, code="LABEL", name="Brand Label", uom="pcs")
    db_session.add_all([comp_front, comp_back, comp_sleeve, comp_collar, comp_label])
    await db_session.flush()

    # 4. Define product BOM (Sleeve=2, others=1)
    bom = BOMHeader(tenant_id=tenant_id, product_id=product.id, version=1, is_active=True)
    db_session.add(bom)
    await db_session.flush()
    
    db_session.add_all([
        BOMLine(bom_header_id=bom.id, component_id=comp_front.id, qty_per_unit=1.0, scrap_pct=0.0),
        BOMLine(bom_header_id=bom.id, component_id=comp_back.id, qty_per_unit=1.0, scrap_pct=0.0),
        BOMLine(bom_header_id=bom.id, component_id=comp_sleeve.id, qty_per_unit=2.0, scrap_pct=0.0),
        BOMLine(bom_header_id=bom.id, component_id=comp_collar.id, qty_per_unit=1.0, scrap_pct=0.0),
        BOMLine(bom_header_id=bom.id, component_id=comp_label.id, qty_per_unit=1.0, scrap_pct=0.0),
    ])
    await db_session.flush()

    # 5. Seed stock (Front=220, Back=180, Sleeve=600, Collar=1000, Label=900)
    stock_seed = [
        (comp_front.id, 220.0),
        (comp_back.id, 180.0),
        (comp_sleeve.id, 600.0),
        (comp_collar.id, 1000.0),
        (comp_label.id, 900.0),
    ]
    for c_id, qty in stock_seed:
        db_session.add(
            Inventory(
                tenant_id=tenant_id,
                component_id=c_id,
                warehouse_id=warehouse.id,
                on_hand_qty=qty,
                reserved_qty=0.0,
                allocated_qty=0.0,
                wip_qty=0.0,
                damaged_qty=0.0
            )
        )
    await db_session.flush()

    # 6. Create Sales Order (500 units)
    so = SalesOrder(id=uuid.uuid4(), tenant_id=tenant_id, order_no="SO-1024", customer_id=uuid.uuid4(), status="open")
    db_session.add(so)
    await db_session.flush()
    so_line = SalesOrderLine(sales_order_id=so.id, product_id=product.id, qty_ordered=500.0, qty_produced=0.0)
    db_session.add(so_line)
    await db_session.commit()

    # --- TEST PURCHASING LIFECYCLE ---
    # We need:
    # Front Panel shortfall: 500 - 220 = 280
    # Back Panel shortfall: 500 - 180 = 320
    # Sleeve shortfall: (500 * 2) - 600 = 400
    
    # 7. Create Purchase Order for shortfalls
    po = PurchaseOrder(
        tenant_id=tenant_id,
        org_id=org_id,
        supplier_id=supplier.id,
        po_no="PO-999",
        status="draft"
    )
    db_session.add(po)
    await db_session.flush()
    
    lines = [
        PurchaseOrderLine(tenant_id=tenant_id, po_id=po.id, component_id=comp_front.id, qty_ordered=280.0, unit_cost=5.00),
        PurchaseOrderLine(tenant_id=tenant_id, po_id=po.id, component_id=comp_back.id, qty_ordered=320.0, unit_cost=5.00),
        PurchaseOrderLine(tenant_id=tenant_id, po_id=po.id, component_id=comp_sleeve.id, qty_ordered=400.0, unit_cost=3.00),
    ]
    db_session.add_all(lines)
    await db_session.commit()
    
    assert po.status == "draft"

    # 8. Approve PO
    po.status = "ordered"
    await db_session.commit()
    assert po.status == "ordered"

    # Eager load PO with lines
    po_query = await db_session.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.lines))
        .where(PurchaseOrder.id == po.id)
    )
    po = po_query.scalar_one()

    # 9. Receive PO -> Update stock balances
    for line in po.lines:
        adj = InventoryAdjustment(
            component_id=line.component_id,
            warehouse_id=warehouse.id,
            qty=line.qty_ordered,
            movement_type="grn"
        )
        await InventoryService.adjust_stock(db=db_session, adjustment=adj, user_id=user.id)
    po.status = "received"
    await db_session.commit()
    assert po.status == "received"

    # 10. Check that inventory is received and matches 500 target for all components!
    bal_front = await InventoryService.get_inventory_balance(db_session, comp_front.id, warehouse.id)
    bal_back = await InventoryService.get_inventory_balance(db_session, comp_back.id, warehouse.id)
    bal_sleeve = await InventoryService.get_inventory_balance(db_session, comp_sleeve.id, warehouse.id)
    
    assert float(bal_front.on_hand_qty) == 500.0  # 220 + 280
    assert float(bal_back.on_hand_qty) == 500.0   # 180 + 320
    assert float(bal_sleeve.on_hand_qty) == 1000.0 # 600 + 400

    # --- TEST PRODUCTION SHOP-FLOOR FLOW ---
    # 11. Schedule Production Order for 500 units linked to Sales Order
    prod_order = ProductionOrder(
        tenant_id=tenant_id,
        org_id=org_id,
        product_id=product.id,
        sales_order_id=so.id,
        target_qty=500.0,
        status="scheduled"
    )
    db_session.add(prod_order)
    await db_session.flush()

    # Create work routing stages
    stages = ["cutting", "stitching", "finishing", "packing"]
    work_orders = []
    for idx, stage in enumerate(stages):
        wo = WorkOrder(
            tenant_id=tenant_id,
            production_order_id=prod_order.id,
            stage=stage,
            sequence_no=idx + 1,
            status="pending"
        )
        db_session.add(wo)
        work_orders.append(wo)
    await db_session.flush()

    # Reserve the components (Front=500, Back=500, Sleeve=1000, Collar=500, Label=500)
    components_to_reserve = [
        (comp_front.id, 500.0),
        (comp_back.id, 500.0),
        (comp_sleeve.id, 1000.0),
        (comp_collar.id, 500.0),
        (comp_label.id, 500.0),
    ]
    
    reservations = []
    for c_id, qty in components_to_reserve:
        res_in = ReservationCreate(
            component_id=c_id,
            warehouse_id=warehouse.id,
            quantity=qty,
            source_order_id=prod_order.id
        )
        res = await InventoryService.create_reservation(db=db_session, res_in=res_in)
        reservations.append(res)
    await db_session.commit()

    # Verify soft reservations are updated in inventory balances (available = on_hand - reserved)
    bal_front = await InventoryService.get_inventory_balance(db_session, comp_front.id, warehouse.id)
    assert float(bal_front.reserved_qty) == 500.0
    assert bal_front.available_qty == 0.00 # 500.0 on hand - 500.0 reserved = 0.0

    # 12. Transition Work Order stages
    # Stage 1: cutting (pending -> active)
    work_orders[0].status = "active"
    prod_order.status = "wip"
    await db_session.commit()
    assert prod_order.status == "wip"

    # Stage 1: cutting -> completed, Stage 2: stitching -> active
    work_orders[0].status = "completed"
    work_orders[1].status = "active"
    await db_session.commit()

    # Complete stitching and finishing stages
    work_orders[1].status = "completed"
    work_orders[2].status = "active"
    await db_session.commit()
    work_orders[2].status = "completed"
    await db_session.commit()

    # 13. Stage 4: packing (the final stage) -> completed
    work_orders[3].status = "active"
    await db_session.commit()
    work_orders[3].status = "completed"
    
    # packing completed -> complete production order, consume reservations
    prod_order.status = "completed"

    # Resolve active reservations
    for r in reservations:
        r.status = "completed"
        
        # Deduct physical stock
        stock = await InventoryService.get_inventory_balance(db_session, r.component_id, warehouse.id)
        stock.on_hand_qty = float(stock.on_hand_qty) - float(r.quantity)
        stock.reserved_qty = float(stock.reserved_qty) - float(r.quantity)
        
        # Log to ledger
        db_session.add(
            StockMovement(
                tenant_id=tenant_id,
                component_id=r.component_id,
                warehouse_id=warehouse.id,
                movement_type="adjustment",
                qty=-r.quantity,
                reference_type="production_order",
                reference_id=prod_order.id,
                created_by=user.id
            )
        )

    # 14. Increment yield on the Sales Order Line!
    if prod_order.sales_order_id:
        so_line.qty_produced = float(so_line.qty_produced) + float(prod_order.target_qty)
        if float(so_line.qty_produced) >= float(so_line.qty_ordered):
            so.status = "fulfilled"

    await db_session.commit()

    # 15. Final Assertion Checks
    # - Raw stock decreased to 0.0 (fully consumed)
    # - Reservations decreased to 0.0
    # - Production Order status is completed
    # - Sales Order status is fulfilled
    # - Sales Order Line qty_produced is 500
    
    final_front = await InventoryService.get_inventory_balance(db_session, comp_front.id, warehouse.id)
    assert float(final_front.on_hand_qty) == 0.0
    assert float(final_front.reserved_qty) == 0.0
    
    assert prod_order.status == "completed"
    assert so.status == "fulfilled"
    assert float(so_line.qty_produced) == 500.0

    print("Purchasing and shop-floor execution integration test completed successfully!")
