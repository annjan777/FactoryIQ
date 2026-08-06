import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, ForeignKey, Boolean, JSON, ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.session import Base

class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    subdomain: Mapped[str] = mapped_column(String(63), unique=True, nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(50), default="standard") # standard, enterprise
    isolation_mode: Mapped[str] = mapped_column(String(20), default="rls") # rls, schema, dedicated
    status: Mapped[str] = mapped_column(String(20), default="active") # active, suspended
    subscription_status: Mapped[str] = mapped_column(String(20), default="active") # active, trial, grace_period, expired, suspended
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    industry_type: Mapped[str] = mapped_column(String(50), default="garment") # garment, furniture, electronics, custom
    max_products_limit: Mapped[int] = mapped_column(default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    organizations: Mapped[List["Organization"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    users: Mapped[List["User"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    roles: Mapped[List["Role"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str] = mapped_column(String(50), default="garment")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="organizations")
    users: Mapped[List["User"]] = relationship(back_populates="organization", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active") # active, suspended
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="users")
    organization: Mapped["Organization"] = relationship(back_populates="users")
    roles: Mapped[List["Role"]] = relationship(secondary="user_roles", back_populates="users")

class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False) # admin, planner, store_keeper, etc.
    permissions: Mapped[dict] = mapped_column(JSON, default=list) # JSON list of permissions

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="roles")
    users: Mapped[List["User"]] = relationship(secondary="user_roles", back_populates="roles")

class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    warehouse_scope: Mapped[Optional[List[uuid.UUID]]] = mapped_column(ARRAY(UUID), nullable=True) # Scope limiting
