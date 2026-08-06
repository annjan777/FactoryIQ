import pytest
import pytest_asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text

from db.session import Base
from modules.auth.models import Tenant, Organization, User
from modules.bom.models import Warehouse, Product, Component, BOMHeader, BOMLine
from modules.inventory.models import Inventory
from modules.sales.models import SalesOrder, SalesOrderLine
from modules.sales.service import FeasibilityService

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import ARRAY

@compiles(ARRAY, 'sqlite')
def compile_array_sqlite(element, compiler, **kw):
    return "TEXT"

# Setup an async sqlite database in-memory for testing
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    # Register PG set_config function stub inside SQLite connection
    from sqlalchemy import event
    @event.listens_for(engine.sync_engine, "connect")
    def register_sqlite_stubs(dbapi_connection, connection_record):
        # Storing parameters in the connection_record's info dict to simulate session state
        def set_config(name, val, is_local):
            connection_record.info[name] = val
            return val
            
        def current_setting(name, is_local=True):
            return connection_record.info.get(name)
            
        dbapi_connection.create_function("set_config", 3, set_config)
        dbapi_connection.create_function("current_setting", 2, current_setting)
        
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        yield session
        await session.close()
        
    await engine.dispose()

@pytest.mark.asyncio
async def test_tshirt_feasibility_scenario(db_session: AsyncSession):
    # 1. Setup Tenant and organization context
    tenant_id = uuid.uuid4()
    org_id = uuid.uuid4()
    
    tenant = Tenant(id=tenant_id, name="GarmentCorp", subdomain="garment", plan="standard")
    org = Organization(id=org_id, tenant_id=tenant_id, name="GarmentCorp HQ", industry="garment")
    
    db_session.add(tenant)
    db_session.add(org)
    await db_session.flush()

    # Simulate RLS context by setting the app.current_tenant session parameter
    # Since SQLite doesn't natively enforce Postgres RLS, this tests that the query parameters and services execute
    await db_session.execute(
        text("SELECT set_config('app.current_tenant', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)}
    )

    # 2. Create Warehouse
    warehouse = Warehouse(
        tenant_id=tenant_id,
        org_id=org_id,
        code="WH-1",
        name="Finished Goods & Materials"
    )
    db_session.add(warehouse)
    await db_session.flush()

    # 3. Create Product (Round Neck T-Shirt)
    product = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        org_id=org_id,
        sku="TSHIRT-RN-101",
        name="Round Neck T-Shirt"
    )
    db_session.add(product)
    await db_session.flush()

    # 4. Create Components (Front Panel, Back Panel, Sleeves, Collars, Labels)
    comp_front = Component(tenant_id=tenant_id, org_id=org_id, code="FRONT-PANEL", name="Front Panel", uom="pcs")
    comp_back = Component(tenant_id=tenant_id, org_id=org_id, code="BACK-PANEL", name="Back Panel", uom="pcs")
    comp_sleeve = Component(tenant_id=tenant_id, org_id=org_id, code="SLEEVE", name="Sleeve Pair", uom="pcs")
    comp_collar = Component(tenant_id=tenant_id, org_id=org_id, code="COLLAR", name="Collar", uom="pcs")
    comp_label = Component(tenant_id=tenant_id, org_id=org_id, code="LABEL", name="Brand Label", uom="pcs")
    
    db_session.add_all([comp_front, comp_back, comp_sleeve, comp_collar, comp_label])
    await db_session.flush()

    # 5. Create BOM (1:1 except Sleeve which requires 2)
    bom = BOMHeader(tenant_id=tenant_id, product_id=product.id, version=1, is_active=True)
    db_session.add(bom)
    await db_session.flush()

    line_front = BOMLine(bom_header_id=bom.id, component_id=comp_front.id, qty_per_unit=1.0, scrap_pct=0.0)
    line_back = BOMLine(bom_header_id=bom.id, component_id=comp_back.id, qty_per_unit=1.0, scrap_pct=0.0)
    line_sleeve = BOMLine(bom_header_id=bom.id, component_id=comp_sleeve.id, qty_per_unit=2.0, scrap_pct=0.0)
    line_collar = BOMLine(bom_header_id=bom.id, component_id=comp_collar.id, qty_per_unit=1.0, scrap_pct=0.0)
    line_label = BOMLine(bom_header_id=bom.id, component_id=comp_label.id, qty_per_unit=1.0, scrap_pct=0.0)
    
    db_session.add_all([line_front, line_back, line_sleeve, line_collar, line_label])
    await db_session.flush()

    # 6. Seed Inventory (Front=220, Back=180, Sleeve=600, Collar=1000, Label=900)
    inv_front = Inventory(tenant_id=tenant_id, component_id=comp_front.id, warehouse_id=warehouse.id, on_hand_qty=220.0, reserved_qty=0.0)
    inv_back = Inventory(tenant_id=tenant_id, component_id=comp_back.id, warehouse_id=warehouse.id, on_hand_qty=180.0, reserved_qty=0.0)
    inv_sleeve = Inventory(tenant_id=tenant_id, component_id=comp_sleeve.id, warehouse_id=warehouse.id, on_hand_qty=600.0, reserved_qty=0.0)
    inv_collar = Inventory(tenant_id=tenant_id, component_id=comp_collar.id, warehouse_id=warehouse.id, on_hand_qty=1000.0, reserved_qty=0.0)
    inv_label = Inventory(tenant_id=tenant_id, component_id=comp_label.id, warehouse_id=warehouse.id, on_hand_qty=900.0, reserved_qty=0.0)
    
    db_session.add_all([inv_front, inv_back, inv_sleeve, inv_collar, inv_label])
    await db_session.flush()

    # 7. Create Sales Order (500 units)
    so = SalesOrder(id=uuid.uuid4(), tenant_id=tenant_id, order_no="SO-1024", customer_id=uuid.uuid4())
    db_session.add(so)
    await db_session.flush()

    so_line = SalesOrderLine(sales_order_id=so.id, product_id=product.id, qty_ordered=500.0)
    db_session.add(so_line)
    await db_session.commit()

    # 8. Run Feasibility Calculation
    feasibility = await FeasibilityService.evaluate_order(db=db_session, sales_order_id=so.id)

    # 9. Asserts matching the guide worked example
    # - Can Produce = 180 (limited by Back Panel = 180)
    # - Shortfall = 320
    # - Readiness % = 36%
    assert feasibility.requested_qty == 500.0
    assert feasibility.producible_qty == 180.0
    assert feasibility.shortfall_qty == 320.0
    assert feasibility.readiness_pct == 36.00

    # Bottleneck component check
    assert len(feasibility.limiting_components) == 1
    limiting = feasibility.limiting_components[0]
    assert limiting.component_code == "BACK-PANEL"
    assert limiting.available_qty == 180.0
    assert limiting.required_qty == 500.0
    assert limiting.shortfall_qty == 320.0

    # Purchase recommendations PO:
    # Front Panel: 220 available - 500 required = 280 shortage
    # Back Panel: 180 available - 500 required = 320 shortage
    po_recs = {rec.component_code: rec.qty for rec in feasibility.recommended_purchase_orders}
    assert len(po_recs) == 3
    assert po_recs["FRONT-PANEL"] == 280.0
    assert po_recs["BACK-PANEL"] == 320.0
    assert po_recs["SLEEVE"] == 400.0

