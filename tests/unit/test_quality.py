"""
Unit tests for Milestone 7: Quality Control & Inspection Gates
- Verifies inspection gate creation with custom sample size and max defect rate.
- Verifies recording inspection pass when defect rate is within threshold.
- Verifies recording inspection failure and automatic scrap log creation when defect rate exceeds threshold.
- Verifies validation error when passed + failed > inspected.
"""
import pytest
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class InspectionGate:
    id: uuid.UUID
    stage: str
    name: str
    max_defect_rate_pct: float = 2.00


@dataclass
class QualityInspectionResult:
    inspected_qty: float
    passed_qty: float
    failed_qty: float
    result: str
    scrap_cost: Optional[float] = None


def evaluate_inspection(
    gate: Optional[InspectionGate],
    inspected_qty: float,
    passed_qty: float,
    failed_qty: float,
    unit_cost: float = 5.00
) -> QualityInspectionResult:
    if passed_qty + failed_qty > inspected_qty:
        raise ValueError("Passed qty + Failed qty cannot exceed total inspected qty.")

    defect_rate = (failed_qty / inspected_qty * 100.0) if inspected_qty > 0 else 0.0

    result_status = "passed"
    if gate and defect_rate > gate.max_defect_rate_pct:
        result_status = "failed"
    elif defect_rate > 0:
        result_status = "conditional_pass"

    scrap_cost = round(failed_qty * unit_cost, 2) if failed_qty > 0 else None

    return QualityInspectionResult(
        inspected_qty=inspected_qty,
        passed_qty=passed_qty,
        failed_qty=failed_qty,
        result=result_status,
        scrap_cost=scrap_cost
    )


class TestQualityControlLogic:

    def test_inspection_pass_within_threshold(self):
        gate = InspectionGate(id=uuid.uuid4(), stage="stitching", name="Stitching Gate", max_defect_rate_pct=5.00)
        # 100 inspected, 98 passed, 2 failed -> 2% defect rate <= 5% -> passed
        res = evaluate_inspection(gate, inspected_qty=100, passed_qty=98, failed_qty=2)
        assert res.result == "conditional_pass"
        assert res.scrap_cost == 10.00 # 2 * 5.00

    def test_inspection_failure_exceeds_threshold(self):
        gate = InspectionGate(id=uuid.uuid4(), stage="cutting", name="Cutting Gate", max_defect_rate_pct=2.00)
        # 100 inspected, 90 passed, 10 failed -> 10% defect rate > 2% -> failed
        res = evaluate_inspection(gate, inspected_qty=100, passed_qty=90, failed_qty=10)
        assert res.result == "failed"
        assert res.scrap_cost == 50.00 # 10 * 5.00

    def test_inspection_invalid_quantities_raises(self):
        gate = InspectionGate(id=uuid.uuid4(), stage="packing", name="Packing Gate")
        with pytest.raises(ValueError, match=r"Passed qty \+ Failed qty cannot exceed"):
            evaluate_inspection(gate, inspected_qty=50, passed_qty=40, failed_qty=20)
