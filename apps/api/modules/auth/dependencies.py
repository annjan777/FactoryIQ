from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import uuid

from core.config import settings
from db.session import get_db
from modules.auth.models import User, Role
from modules.auth.utils import decode_access_token

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

async def get_current_user(
    token: str = Depends(reusable_oauth2),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
        
    user_id: str = payload.get("sub")
    tenant_id: str = payload.get("tenant_id")
    if user_id is None or tenant_id is None:
        raise credentials_exception
        
    # Query user and eager load roles and tenant
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles), selectinload(User.tenant))
        .where(User.id == uuid.UUID(user_id), User.tenant_id == uuid.UUID(tenant_id))
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
        
    return user

async def get_current_tenant_id(
    current_user: User = Depends(get_current_user)
) -> uuid.UUID:
    return current_user.tenant_id

class PermissionChecker:
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        # Check if user has a role with the required permission
        for role in current_user.roles:
            # permissions is a JSON list of strings, e.g., ["view_inventory", "adjust_inventory"]
            permissions_list = role.permissions
            if isinstance(permissions_list, list) and self.required_permission in permissions_list:
                return current_user
                
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have the required permission: {self.required_permission}"
        )
