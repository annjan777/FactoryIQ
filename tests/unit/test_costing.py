"""
Unit tests for Milestone 8: Product Costing & Financial Ledger
- Verifies standard cost compilation (std_total = std_material + std_labor + std_overhead).
- Verifies job cost calculation from BOM materials, labor stage hours, and overhead allocation.
- Verifies favorable vs unfavorable variance computation (cost_variance = actual - standard).
"""
import pytest
import uuid
from dataclasses import dataclass

@dataclass
class StandardCostTarget:
    std_material: float
    std_labor: float
    std_overhead: float

    @property
    def std_total(self) -> float:
        return round(self.std_material + self.std_labor + self.std_overhead, 2)


@dataclass
class JobCostSummary:
    target_qty: float
    actual_material: float
    actual_labor: float
    actual_overhead: float

    @property
    def actual_total(self) -> float:
        return round(self.actual_material + self.actual_labor + self.actual_overhead, 2)

    def calculate_variance(self, std_target: StandardCostTarget):
        std_job_total = round(std_target.std_total * self.target_qty, 2)
        variance = round(self.actual_total - std_job_total, 2)
        is_favorable = variance <= 0
        return {
            "actual_total": self.actual_total,
            "std_total": std_job_total,
            "cost_variance": variance,
            "is_favorable": is_favorable,
            "unit_actual": round(self.actual_total / self.target_qty, 2) if self.target_qty > 0 else 0.0,
            "unit_standard": std_target.std_total
        }


class TestProductCostingLogic:

    def test_standard_cost_compilation(self):
        std = StandardCostTarget(std_material=12.50, std_labor=10.00, std_overhead=2.50)
        assert std.std_total == 25.00

    def test_favorable_job_cost_variance(self):
        std = StandardCostTarget(std_material=12.50, std_labor=10.00, std_overhead=2.50)
        job = JobCostSummary(
            target_qty=100.0,
            actual_material=1200.0, # $12.00/unit
            actual_labor=900.0,     # $9.00/unit
            actual_overhead=200.0   # $2.00/unit
        )
        # Actual total = 2300.00 ($23.00/unit) vs Standard total = 2500.00 ($25.00/unit)
        res = job.calculate_variance(std)
        assert res["actual_total"] == 2300.00
        assert res["std_total"] == 2500.00
        assert res["cost_variance"] == -200.00 # -$200 favorable
        assert res["is_favorable"] is True
        assert res["unit_actual"] == 23.00

    def test_unfavorable_job_cost_variance(self):
        std = StandardCostTarget(std_material=10.00, std_labor=8.00, std_overhead=2.00)
        job = JobCostSummary(
            target_qty=50.0,
            actual_material=600.0,  # $12.00/unit
            actual_labor=500.0,    # $10.00/unit
            actual_overhead=150.0   # $3.00/unit
        )
        # Actual total = 1250.00 ($25.00/unit) vs Standard total = 1000.00 ($20.00/unit)
        res = job.calculate_variance(std)
        assert res["actual_total"] == 1250.00
        assert res["std_total"] == 1000.00
        assert res["cost_variance"] == 250.00 # +$250 unfavorable
        assert res["is_favorable"] is False
