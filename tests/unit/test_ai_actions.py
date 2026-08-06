import pytest
import pytest_asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text, select
from sqlalchemy.orm import selectinload

from db.session import Base
from modules.auth.models import Tenant, Organization, User
from modules.bom.models import Warehouse, Product, Component, BOMHeader, BOMLine
from modules.inventory.models import Inventory, InventoryReservation
from modules.sales.models import SalesOrder, SalesOrderLine
from modules.purchasing.models import Supplier, PurchaseOrder
from modules.production.models import ProductionOrder, WorkOrder
from modules.ai_assistant.service import AIAssistantService

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
async def test_ai_conversational_actions(db_session: AsyncSession):
    # 1. Setup tenant, org, user context
    tenant_id = uuid.uuid4()
    org_id = uuid.uuid4()
    
    tenant = Tenant(id=tenant_id, name="AI Garments Ltd", subdomain="aigarment", plan="standard")
    org = Organization(id=org_id, tenant_id=tenant_id, name="Shop Floor HQ", industry="garment")
    user = User(id=uuid.uuid4(), tenant_id=tenant_id, org_id=org_id, email="ai@garment.com", password_hash="hash", status="active")
    
    db_session.add_all([tenant, org, user])
    await db_session.flush()

    # Seed mock RLS parameters
    await db_session.execute(
        text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
        {"tenant_id": str(tenant_id)}
    )

    # 2. Setup Warehouse & Supplier
    warehouse = Warehouse(tenant_id=tenant_id, org_id=org_id, code="WH-1", name="Main Warehouse")
    supplier = Supplier(tenant_id=tenant_id, org_id=org_id, code="SUPP-01", name="Thread Provider")
    db_session.add_all([warehouse, supplier])
    await db_session.flush()

    # 3. Create Product (T-Shirt) & Components
    product = Product(id=uuid.uuid4(), tenant_id=tenant_id, org_id=org_id, sku="TSHIRT-RN-101", name="Round Neck T-Shirt")
    db_session.add(product)
    
    comp_front = Component(tenant_id=tenant_id, org_id=org_id, code="FRONT-PANEL", name="Front Panel", uom="pcs")
    comp_back = Component(tenant_id=tenant_id, org_id=org_id, code="BACK-PANEL", name="Back Panel", uom="pcs")
    db_session.add_all([comp_front, comp_back])
    await db_session.flush()

    # 4. Define BOM
    bom = BOMHeader(tenant_id=tenant_id, product_id=product.id, version=1, is_active=True)
    db_session.add(bom)
    await db_session.flush()
    
    db_session.add_all([
        BOMLine(bom_header_id=bom.id, component_id=comp_front.id, qty_per_unit=1.0, scrap_pct=0.0),
        BOMLine(bom_header_id=bom.id, component_id=comp_back.id, qty_per_unit=1.0, scrap_pct=0.0)
    ])
    await db_session.flush()

    # 5. Seed stock (Front=200, Back=150) -> Shortages for 500 garments: Front=300, Back=350
    db_session.add_all([
        Inventory(tenant_id=tenant_id, component_id=comp_front.id, warehouse_id=warehouse.id, on_hand_qty=200.0),
        Inventory(tenant_id=tenant_id, component_id=comp_back.id, warehouse_id=warehouse.id, on_hand_qty=150.0),
    ])
    await db_session.flush()

    # 6. Create Sales Order (500 units)
    so = SalesOrder(id=uuid.uuid4(), tenant_id=tenant_id, order_no="SO-1024", customer_id=uuid.uuid4(), status="open")
    db_session.add(so)
    await db_session.flush()
    so_line = SalesOrderLine(sales_order_id=so.id, product_id=product.id, qty_ordered=500.0, qty_produced=0.0)
    db_session.add(so_line)
    await db_session.commit()

    # --- VERIFY AI PURCHASE ORDER TRIGGER ---
    # User message: "order the missing items for SO-1024"
    intent_info = await AIAssistantService.classify_intent("order the missing items for SO-1024", context={"active_order": "SO-1024"})
    assert intent_info["intent"] == "create_po"
    assert intent_info["entities"]["order_no"] == "SO-1024"

    # Execute action
    res = await AIAssistantService.route_and_execute(db_session, intent_info, user)
    assert "error" not in res
    assert res["status"] == "draft"
    assert res["lines_count"] == 2  # Front panel (300) and Back panel (350)
    
    # Check that PO exists in db
    po_q = await db_session.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.lines)).where(PurchaseOrder.po_no == res["po_no"])
    )
    po = po_q.scalar_one()
    assert len(po.lines) == 2
    assert float(po.lines[0].qty_ordered) in [300.0, 350.0]

    # --- VERIFY AI WORK ORDER STAGE TRANSITION ---
    # Setup production order run manually in wip state
    po_run = ProductionOrder(tenant_id=tenant_id, org_id=org_id, product_id=product.id, target_qty=500.0, status="scheduled")
    db_session.add(po_run)
    await db_session.flush()
    
    wo_cutting = WorkOrder(tenant_id=tenant_id, production_order_id=po_run.id, stage="cutting", sequence_no=1, status="pending")
    wo_stitching = WorkOrder(tenant_id=tenant_id, production_order_id=po_run.id, stage="stitching", sequence_no=2, status="pending")
    db_session.add_all([wo_cutting, wo_stitching])
    await db_session.commit()

    # User message: "start the cutting stage"
    intent_info = await AIAssistantService.classify_intent("start the cutting stage")
    assert intent_info["intent"] == "transition_work_order"
    assert intent_info["entities"]["stage"] == "cutting"
    assert intent_info["entities"]["target_status"] == "active"

    # Execute stage transition via AI
    transition_res = await AIAssistantService.route_and_execute(db_session, intent_info, user)
    assert "error" not in transition_res
    assert transition_res["stage"] == "cutting"
    assert transition_res["status"] == "active"
    assert transition_res["production_order_status"] == "wip"

    # Check work order status in db
    await db_session.refresh(wo_cutting)
    assert wo_cutting.status == "active"

    print("Conversational AI action integration tests completed successfully!")
