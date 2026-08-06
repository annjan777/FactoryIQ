import uuid
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from db.session import get_db
from modules.auth.dependencies import get_current_user

from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status

async def get_tenant_db(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> AsyncSession:
    """
    Dependency that sets the database isolation context for the request.
    Enforces Subscription Kill-Switch checks before opening tenant connection session.
    """
    tenant = current_user.tenant
    
    # ── Subscription Kill-Switch Enforcement ────────────────────────────
    if tenant:
        if tenant.status == "suspended" or tenant.subscription_status in ["expired", "suspended"]:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Subscription expired or account suspended. Kill-Switch activated. Please contact platform superadmin.",
            )
        if tenant.subscription_expires_at and datetime.now(timezone.utc) > tenant.subscription_expires_at:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Subscription trial period ended. Kill-Switch activated. Please renew access.",
            )

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

