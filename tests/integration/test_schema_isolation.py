import pytest
import pytest_asyncio
import uuid
from sqlalchemy import text, select
from sqlalchemy.orm import selectinload

from db.session import async_session
from modules.auth.models import Tenant, User, Role
from modules.auth.schemas import TenantCreate, UserCreate
from modules.auth.router import register_tenant

@pytest.mark.asyncio
async def test_premium_schema_isolation():
    """
    Integration test verifying that:
    1. A tenant with isolation_mode="schema" creates a private PostgreSQL schema.
    2. Tables are provisioned inside the private schema.
    3. Default Role and User records are written to the private schema tables.
    """
    session = async_session()
    try:
        # Generate a unique subdomain to avoid clashing with other tests/tenants
        unique_id = uuid.uuid4().hex[:6]
        subdomain = f"corp-{unique_id}"
        schema_name = f"tenant_{subdomain}"

        tenant_in = TenantCreate(
            name="Premium Corp",
            subdomain=subdomain,
            plan="enterprise",
            isolation_mode="schema"
        )
        admin_in = UserCreate(
            email=f"admin@{subdomain}.com",
            password="password123",
            first_name="Admin",
            last_name="Premium"
        )

        # 1. Execute tenant registration
        try:
            admin_user = await register_tenant(tenant_in=tenant_in, admin_in=admin_in, db=session)
            assert admin_user.email == admin_in.email
            print(f"Registered premium tenant with subdomain: {subdomain}")
        except Exception as reg_err:
            print(f"Registration failed with: {str(reg_err)}")
            # Rollback first to clear the transaction block
            await session.rollback()
            # Query existing tables in schema
            tables_res = await session.execute(
                text("SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema LIKE 'tenant_%'")
            )
            print("Existing tables in custom schemas:", tables_res.all())
            raise reg_err

        # 2. Check that the schema exists in the database
        schema_check = await session.execute(
            text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"),
            {"schema": schema_name}
        )
        assert schema_check.scalar() == schema_name
        print(f"Verified schema exists: {schema_name}")

        # 3. Verify that the tables exist in the custom schema (e.g. check roles table exists there)
        table_check = await session.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = :schema AND table_name = 'roles'"),
            {"schema": schema_name}
        )
        assert table_check.scalar() == "roles"
        print("Verified tables created inside the schema.")

        # 4. Query the roles table in the schema using search_path and check that the default TenantAdmin role exists
        await session.execute(text(f'SET search_path TO "{schema_name}", public'))
        roles_result = await session.execute(select(Role).where(Role.name == "TenantAdmin"))
        admin_role = roles_result.scalar_one_or_none()
        assert admin_role is not None
        print("Verified default TenantAdmin role exists inside schema tables.")

        # Cleanup: Drop the test schema to keep the DB clean
        await session.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        # Delete tenant from global tenants table
        await session.execute(
            text("DELETE FROM tenants WHERE subdomain = :subdomain"),
            {"subdomain": subdomain}
        )
        await session.commit()
        print("Cleanup completed successfully.")
        
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()
