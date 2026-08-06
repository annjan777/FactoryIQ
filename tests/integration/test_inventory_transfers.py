import pytest
import pytest_asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text, select
from sqlalchemy.orm import selectinload

from db.session import Base
from modules.auth.models import Tenant, User
from modules.bom.models import Warehouse, Component
from modules.inventory.models import Inventory, StockMovement
from modules.inventory.service import InventoryService
from modules.inventory.schemas import InventoryAdjustment, InventoryTransferCreate

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
        
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
        
    await engine.dispose()

@pytest.mark.asyncio
async def test_multi_warehouse_transfers(db_session: AsyncSession):
    # 1. Setup Tenant and User
    tenant_id = uuid.uuid4()
    tenant = Tenant(
        id=tenant_id,
        name="Transfers Inc",
        subdomain="transfersinc",
        plan="standard",
        isolation_mode="rls"
    )
    db_session.add(tenant)
    
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        tenant_id=tenant_id,
        org_id=uuid.uuid4(), # dummy org
        email="admin@transfersinc.com",
        password_hash="passwordhash"
    )
    db_session.add(user)
    await db_session.flush()

    # Bind active tenant context
    await db_session.execute(
        text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
        {"tenant_id": str(tenant_id)}
    )

    # 2. Setup Warehouses and Component
    wh_source_id = uuid.uuid4()
    wh_source = Warehouse(
        id=wh_source_id,
        tenant_id=tenant_id,
        org_id=user.org_id,
        code="WH-SRC",
        name="Source Materials Warehouse"
    )
    db_session.add(wh_source)

    wh_dest_id = uuid.uuid4()
    wh_dest = Warehouse(
        id=wh_dest_id,
        tenant_id=tenant_id,
        org_id=user.org_id,
        code="WH-DST",
        name="Production Floor Hub"
    )
    db_session.add(wh_dest)

    comp_id = uuid.uuid4()
    comp = Component(
        id=comp_id,
        tenant_id=tenant_id,
        org_id=user.org_id,
        code="FABRIC",
        name="Cotton Fabric",
        uom="mtr"
    )
    db_session.add(comp)
    await db_session.flush()

    # 3. Seed Stock at Source Warehouse
    adj = InventoryAdjustment(
        component_id=comp_id,
        warehouse_id=wh_source_id,
        qty=100.0,
        movement_type="grn"
    )
    await InventoryService.adjust_stock(db=db_session, adjustment=adj, user_id=user_id)
    await db_session.commit()

    # Verify source warehouse has 100 on hand
    src_balance = await InventoryService.get_inventory_balance(db_session, comp_id, wh_source_id)
    assert src_balance.on_hand_qty == 100.0
    assert src_balance.available_qty == 100.0

    # 4. Perform valid transfer of 40 units
    updated_stocks = await InventoryService.transfer_stock(
        db=db_session,
        from_warehouse_id=wh_source_id,
        to_warehouse_id=wh_dest_id,
        component_id=comp_id,
        qty=40.0,
        user_id=user_id
    )
    await db_session.commit()

    assert len(updated_stocks) == 2
    # Verify stock decremented at source, incremented/created at destination
    src_balance = await InventoryService.get_inventory_balance(db_session, comp_id, wh_source_id)
    dest_balance = await InventoryService.get_inventory_balance(db_session, comp_id, wh_dest_id)
    assert src_balance.on_hand_qty == 60.0
    assert dest_balance.on_hand_qty == 40.0

    # Verify ledger movements were logged
    movements_res = await db_session.execute(
        select(StockMovement).where(StockMovement.component_id == comp_id).order_by(StockMovement.id.asc())
    )
    movements = movements_res.scalars().all()
    # GRN (100.0), transfer_out (-40.0), transfer_in (40.0)
    assert len(movements) == 3
    assert movements[1].movement_type == "transfer_out"
    assert movements[1].qty == -40.0
    assert movements[1].warehouse_id == wh_source_id
    
    assert movements[2].movement_type == "transfer_in"
    assert movements[2].qty == 40.0
    assert movements[2].warehouse_id == wh_dest_id

    # 5. Verify over-transfer raises ValueError
    with pytest.raises(ValueError) as exc:
        await InventoryService.transfer_stock(
            db=db_session,
            from_warehouse_id=wh_source_id,
            to_warehouse_id=wh_dest_id,
            component_id=comp_id,
            qty=70.0,
            user_id=user_id
        )
    assert "Insufficient stock" in str(exc.value)

    # Verify stock levels remained unchanged (60.0 and 40.0)
    src_balance = await InventoryService.get_inventory_balance(db_session, comp_id, wh_source_id)
    dest_balance = await InventoryService.get_inventory_balance(db_session, comp_id, wh_dest_id)
    assert src_balance.on_hand_qty == 60.0
    assert dest_balance.on_hand_qty == 40.0
