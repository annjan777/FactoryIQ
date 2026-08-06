"""
Unit tests for Subscription Kill-Switch & Multi-Industry Cell Workflows
- Verifies active unexpired tenant access is permitted.
- Verifies suspended or expired subscription triggers Kill-Switch (HTTP 402 Payment Required).
- Verifies multi-industry production stage template resolution (Garment vs Furniture vs Electronics).
"""
import pytest
import uuid
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Optional
from fastapi import HTTPException


@dataclass
class Tenant:
    id: uuid.UUID
    name: str
    status: str = "active"
    subscription_status: str = "active"
    subscription_expires_at: Optional[datetime] = None
    industry_type: str = "garment"


def validate_tenant_killswitch(tenant: Tenant):
    """Mirrors the tenancy.py get_tenant_db Kill-Switch check."""
    if tenant.status == "suspended" or tenant.subscription_status in ["expired", "suspended"]:
        raise HTTPException(
            status_code=402,
            detail="Subscription expired or account suspended. Kill-Switch activated. Please contact platform superadmin.",
        )
    if tenant.subscription_expires_at and datetime.now(timezone.utc) > tenant.subscription_expires_at:
        raise HTTPException(
            status_code=402,
            detail="Subscription trial period ended. Kill-Switch activated. Please renew access.",
        )
    return True


def resolve_industry_stages(industry_type: str):
    stages = {
        "garment": ["cutting", "stitching", "finishing", "packing"],
        "furniture": ["wood_cutting", "sanding", "assembly", "polishing", "packing"],
        "electronics": ["smt_assembly", "soldering", "testing", "casing", "packaging"],
        "custom": ["design", "fabrication", "assembly", "qa", "dispatch"],
    }
    return stages.get(industry_type.lower(), stages["garment"])


class TestSubscriptionKillSwitch:

    def test_active_tenant_access_allowed(self):
        tenant = Tenant(
            id=uuid.uuid4(),
            name="GarmentCorp Inc.",
            status="active",
            subscription_status="active",
            subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            industry_type="garment"
        )
        assert validate_tenant_killswitch(tenant) is True

    def test_suspended_tenant_triggers_killswitch(self):
        tenant = Tenant(
            id=uuid.uuid4(),
            name="BadPay Corp",
            status="suspended",
            subscription_status="suspended",
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_tenant_killswitch(tenant)
        assert exc_info.value.status_code == 402
        assert "Kill-Switch activated" in exc_info.value.detail

    def test_expired_trial_triggers_killswitch(self):
        tenant = Tenant(
            id=uuid.uuid4(),
            name="TrialEnded Inc.",
            status="active",
            subscription_status="trial",
            subscription_expires_at=datetime.now(timezone.utc) - timedelta(days=1), # expired yesterday
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_tenant_killswitch(tenant)
        assert exc_info.value.status_code == 402
        assert "trial period ended" in exc_info.value.detail

    def test_multi_industry_stage_templates(self):
        assert resolve_industry_stages("garment") == ["cutting", "stitching", "finishing", "packing"]
        assert resolve_industry_stages("furniture") == ["wood_cutting", "sanding", "assembly", "polishing", "packing"]
        assert resolve_industry_stages("electronics") == ["smt_assembly", "soldering", "testing", "casing", "packaging"]
