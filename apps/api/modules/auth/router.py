from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from db.session import get_db, Base
from modules.auth.models import Tenant, Organization, User, Role, UserRole
from modules.auth.schemas import TenantCreate, UserCreate, UserResponse, TokenResponse
from modules.auth.utils import verify_password, get_password_hash, create_access_token
from modules.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register-tenant", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_tenant(
    tenant_in: TenantCreate,
    admin_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    # Check subdomain unique
    tenant_exists = await db.execute(select(Tenant).where(Tenant.subdomain == tenant_in.subdomain))
    if tenant_exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A tenant with this subdomain already exists."
        )
        
    # Check email unique
    user_exists = await db.execute(select(User).where(User.email == admin_in.email))
    if user_exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )

    # 1. Create Tenant
    tenant = Tenant(
        name=tenant_in.name,
        subdomain=tenant_in.subdomain,
        plan=tenant_in.plan,
        isolation_mode=tenant_in.isolation_mode
    )
    db.add(tenant)
    await db.flush()
    
    # Bind session or provision schema based on isolation mode
    from sqlalchemy import text
    if tenant.isolation_mode == "schema":
        schema_name = f"tenant_{tenant.subdomain}"
        # 1. Provision target private schema namespace
        await db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
        
        # 2. Compile table structures inside private namespace using connection search path
        conn = await db.connection()
        
        from sqlalchemy.schema import CreateTable
        
        def create_tables(sync_conn):
            # 1. Temporarily isolate search path to only check missing tables in private schema
            sync_conn.execute(text(f'SET search_path TO "{schema_name}"'))
            missing_tables = []
            
            # Base.metadata.sorted_tables is sorted topologically to avoid foreign key errors on creation
            for table in Base.metadata.sorted_tables:
                if table.name != "tenants":
                    if not sync_conn.dialect.has_table(sync_conn, table.name, schema=None):
                        missing_tables.append(table)
            
            # 2. Restore search path and directly execute CreateTable DDL
            if missing_tables:
                sync_conn.execute(text(f'SET search_path TO "{schema_name}", public'))
                for table in missing_tables:
                    sync_conn.execute(CreateTable(table))
            
        await conn.run_sync(create_tables)
        
        # 3. Route subsequent inserts of default org, role, and user to the schema
        await db.execute(text(f'SET search_path TO "{schema_name}", public'))
    else:
        # Fallback standard RLS context binding
        await db.execute(
            text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
            {"tenant_id": str(tenant.id)}
        )
    
    # 2. Create default Organization
    org = Organization(
        tenant_id=tenant.id,
        name=f"{tenant.name} Main HQ",
        industry="garment"
    )
    db.add(org)
    await db.flush()
    
    # 3. Create default Admin Role
    admin_role = Role(
        tenant_id=tenant.id,
        name="TenantAdmin",
        permissions=[
            "view_inventory", "adjust_inventory", "view_bom", "edit_bom",
            "view_sales", "edit_sales", "check_feasibility", "view_production",
            "edit_production", "view_purchasing", "edit_purchasing", "run_mrp", "chat_ai"
        ]
    )
    db.add(admin_role)
    await db.flush()
    
    # 4. Create Admin User
    hashed_password = get_password_hash(admin_in.password)
    user = User(
        tenant_id=tenant.id,
        org_id=org.id,
        email=admin_in.email,
        password_hash=hashed_password,
        status="active"
    )
    db.add(user)
    await db.flush()
    
    # 5. Link Admin User to Role
    user_role_link = UserRole(
        user_id=user.id,
        role_id=admin_role.id,
        warehouse_scope=None # Scope is global for main admin
    )
    db.add(user_role_link)
    
    await db.commit()
    await db.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles))
        .where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Suspended or inactive user account."
        )
        
    # Pick first role name as primary claim, or defaults
    role_name = user.roles[0].name if user.roles else "viewer"
    
    access_token = create_access_token(
        subject=user.id,
        tenant_id=str(user.tenant_id),
        org_id=str(user.org_id),
        role=role_name
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/me", response_model=UserResponse)
async def me(
    current_user: User = Depends(get_current_user)
):
    return current_user
