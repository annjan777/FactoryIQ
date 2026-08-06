import uuid
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from db.session import get_db
from modules.auth.dependencies import get_current_user

async def get_tenant_db(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> AsyncSession:
    """
    Dependency that sets the database isolation context for the request.
    For premium tenants, switches search_path to the private schema.
    For standard tenants, binds the RLS session local variable 'app.current_tenant'.
    """
    tenant = current_user.tenant
    if tenant and tenant.isolation_mode == "schema":
        # Direct premium tenant to their isolated database schema namespace
        schema_name = f"tenant_{tenant.subdomain}"
        # We quote the schema name to ensure subdomains with hyphens are supported safely
        await db.execute(
            text(f'SET search_path TO "{schema_name}", public')
        )
    else:
        # Fallback to shared RLS isolation boundary
        tenant_id = current_user.tenant_id
        await db.execute(
            text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
            {"tenant_id": str(tenant_id)}
        )
    return db
