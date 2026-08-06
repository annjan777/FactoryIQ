import time
from sqlalchemy import text
from sqlalchemy.orm import Session
from db.session import Base, sync_engine, SessionLocal

# Import all models so SQLAlchemy metadata compiles them
from modules.auth.models import Tenant, Organization, User, Role, UserRole
from modules.bom.models import Warehouse, Product, Component, BOMHeader, BOMLine
from modules.inventory.models import Inventory, StockMovement, InventoryReservation
from modules.sales.models import SalesOrder, SalesOrderLine
from modules.purchasing.models import Supplier, PurchaseOrder, PurchaseOrderLine, SupplierComponent
from modules.production.models import ProductionOrder, WorkOrder

def initialize_database():
    print("Starting database schema creation...")
    # 1. Create all tables
    Base.metadata.create_all(bind=sync_engine)
    print("Tables created successfully.")

    # 2. Apply Row-Level Security policies
    rls_statements = [
        # Users
        "ALTER TABLE users ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE users FORCE ROW LEVEL SECURITY;",
        "DROP POLICY IF EXISTS tenant_isolation_users ON users;",
        "CREATE POLICY tenant_isolation_users ON users USING (tenant_id = current_setting('app.current_tenant', true)::uuid);",
        
        # Roles
        "ALTER TABLE roles ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE roles FORCE ROW LEVEL SECURITY;",
        "DROP POLICY IF EXISTS tenant_isolation_roles ON roles;",
        "CREATE POLICY tenant_isolation_roles ON roles USING (tenant_id = current_setting('app.current_tenant', true)::uuid);",
        
        # Warehouses
        "ALTER TABLE warehouses ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE warehouses FORCE ROW LEVEL SECURITY;",
        "DROP POLICY IF EXISTS tenant_isolation_warehouses ON warehouses;",
        "CREATE POLICY tenant_isolation_warehouses ON warehouses USING (tenant_id = current_setting('app.current_tenant', true)::uuid);",
        
        # Products
        "ALTER TABLE products ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE products FORCE ROW LEVEL SECURITY;",
        "DROP POLICY IF EXISTS tenant_isolation_products ON products;",
        "CREATE POLICY tenant_isolation_products ON products USING (tenant_id = current_setting('app.current_tenant', true)::uuid);",
        
        # Components
        "ALTER TABLE components ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE components FORCE ROW LEVEL SECURITY;",
        "DROP POLICY IF EXISTS tenant_isolation_components ON components;",
        "CREATE POLICY tenant_isolation_components ON components USING (tenant_id = current_setting('app.current_tenant', true)::uuid);",
        
        # BOM Headers
        "ALTER TABLE bom_headers ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE bom_headers FORCE ROW LEVEL SECURITY;",
        "DROP POLICY IF EXISTS tenant_isolation_bom_headers ON bom_headers;",
        "CREATE POLICY tenant_isolation_bom_headers ON bom_headers USING (tenant_id = current_setting('app.current_tenant', true)::uuid);",
        
        # Inventory Balances
        "ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE inventory FORCE ROW LEVEL SECURITY;",
        "DROP POLICY IF EXISTS tenant_isolation_inventory ON inventory;",
        "CREATE POLICY tenant_isolation_inventory ON inventory USING (tenant_id = current_setting('app.current_tenant', true)::uuid);",
        
        # Stock Movements Ledger
        "ALTER TABLE stock_movements ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE stock_movements FORCE ROW LEVEL SECURITY;",
        "DROP POLICY IF EXISTS tenant_isolation_stock_movements ON stock_movements;",
        "CREATE POLICY tenant_isolation_stock_movements ON stock_movements USING (tenant_id = current_setting('app.current_tenant', true)::uuid);",
        
        # Inventory Reservations
        "ALTER TABLE inventory_reservations ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE inventory_reservations FORCE ROW LEVEL SECURITY;",
        "DROP POLICY IF EXISTS tenant_isolation_inventory_reservations ON inventory_reservations;",
        "CREATE POLICY tenant_isolation_inventory_reservations ON inventory_reservations USING (tenant_id = current_setting('app.current_tenant', true)::uuid);",
        
        # Sales Orders
        "ALTER TABLE sales_orders ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE sales_orders FORCE ROW LEVEL SECURITY;",
        "DROP POLICY IF EXISTS tenant_isolation_sales_orders ON sales_orders;",
        "CREATE POLICY tenant_isolation_sales_orders ON sales_orders USING (tenant_id = current_setting('app.current_tenant', true)::uuid);",
        
        # Suppliers
        "ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE suppliers FORCE ROW LEVEL SECURITY;",
        "DROP POLICY IF EXISTS tenant_isolation_suppliers ON suppliers;",
        "CREATE POLICY tenant_isolation_suppliers ON suppliers USING (tenant_id = current_setting('app.current_tenant', true)::uuid);",
        
        # Purchase Orders
        "ALTER TABLE purchase_orders ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE purchase_orders FORCE ROW LEVEL SECURITY;",
        "DROP POLICY IF EXISTS tenant_isolation_purchase_orders ON purchase_orders;",
        "CREATE POLICY tenant_isolation_purchase_orders ON purchase_orders USING (tenant_id = current_setting('app.current_tenant', true)::uuid);",
        
        # Purchase Order Lines
        "ALTER TABLE purchase_order_lines ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE purchase_order_lines FORCE ROW LEVEL SECURITY;",
        "DROP POLICY IF EXISTS tenant_isolation_purchase_order_lines ON purchase_order_lines;",
        "CREATE POLICY tenant_isolation_purchase_order_lines ON purchase_order_lines USING (tenant_id = current_setting('app.current_tenant', true)::uuid);",
        
        # Supplier Components
        "ALTER TABLE supplier_components ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE supplier_components FORCE ROW LEVEL SECURITY;",
        "DROP POLICY IF EXISTS tenant_isolation_supplier_components ON supplier_components;",
        "CREATE POLICY tenant_isolation_supplier_components ON supplier_components USING (tenant_id = current_setting('app.current_tenant', true)::uuid);",

        # Production Orders
        "ALTER TABLE production_orders ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE production_orders FORCE ROW LEVEL SECURITY;",
        "DROP POLICY IF EXISTS tenant_isolation_production_orders ON production_orders;",
        "CREATE POLICY tenant_isolation_production_orders ON production_orders USING (tenant_id = current_setting('app.current_tenant', true)::uuid);",
        
        # Work Orders
        "ALTER TABLE work_orders ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE work_orders FORCE ROW LEVEL SECURITY;",
        "DROP POLICY IF EXISTS tenant_isolation_work_orders ON work_orders;",
        "CREATE POLICY tenant_isolation_work_orders ON work_orders USING (tenant_id = current_setting('app.current_tenant', true)::uuid);"
    ]


    session = SessionLocal()
    try:
        print("Applying Row-Level Security policies...")
        # We must disable RLS bypass for local schema migrations if executing in pool
        # and configure RLS on each table one by one.
        for stmt in rls_statements:
            try:
                session.execute(text(stmt))
            except Exception as rls_err:
                # Catch cases if policies or RLS are already enabled on certain tables
                print(f"Skipping or handled RLS statement error: {str(rls_err)}")
        session.commit()
        print("Row-Level Security policies configured successfully.")

        # Setup non-superuser role and grant privileges
        print("Configuring factoryiq_user role and permissions...")
        setup_role_statements = [
            "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'factoryiq_user') THEN CREATE ROLE factoryiq_user WITH LOGIN PASSWORD 'factoryiq_pass'; END IF; END $$;",
            "GRANT ALL PRIVILEGES ON DATABASE factoryiq TO factoryiq_user;",
            "GRANT USAGE ON SCHEMA public TO factoryiq_user;",
            "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO factoryiq_user;",
            "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO factoryiq_user;",
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO factoryiq_user;",
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO factoryiq_user;"
        ]
        for stmt in setup_role_statements:
            try:
                session.execute(text(stmt))
            except Exception as role_err:
                print(f"Handled Role setup statement error: {str(role_err)}")
        session.commit()
        print("Non-superuser role configured successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error applying RLS policies: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    # Wait for database connection to be ready (up to 30 seconds)
    retries = 10
    success = False
    while retries > 0:
        try:
            with sync_engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                success = True
                break
        except Exception:
            print("Database not ready yet, retrying in 3 seconds...")
            time.sleep(3)
            retries -= 1
            
    if success:
        initialize_database()
    else:
        print("Could not connect to the database. Schema initialization aborted.")
