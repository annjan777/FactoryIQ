import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text

from modules.quality.models import InspectionGate, QualityInspection, ScrapLog
from modules.quality.schemas import InspectionGateCreate, QualityInspectionCreate


class QualityService:

    @staticmethod
    async def create_gate(
        db: AsyncSession, tenant_id: uuid.UUID, payload: InspectionGateCreate
    ) -> InspectionGate:
        gate = InspectionGate(
            tenant_id=tenant_id,
            stage=payload.stage,
            name=payload.name,
            sample_size_pct=payload.sample_size_pct,
            max_defect_rate_pct=payload.max_defect_rate_pct,
            is_active=payload.is_active,
        )
        db.add(gate)
        await db.commit()
        await db.refresh(gate)
        return gate

    @staticmethod
    async def list_gates(db: AsyncSession) -> List[InspectionGate]:
        res = await db.execute(select(InspectionGate).where(InspectionGate.is_active == True))
        return res.scalars().all()

    @staticmethod
    async def record_inspection(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        inspector_id: uuid.UUID,
        payload: QualityInspectionCreate,
    ) -> QualityInspection:
        if payload.passed_qty + payload.failed_qty > payload.inspected_qty:
            raise ValueError("Passed qty + Failed qty cannot exceed total inspected qty.")

        defect_rate = (payload.failed_qty / payload.inspected_qty * 100.0) if payload.inspected_qty > 0 else 0.0

        # Determine pass/fail result based on defect rate vs gate threshold
        result_status = "passed"
        if payload.gate_id:
            gate = await db.get(InspectionGate, payload.gate_id)
            if gate and defect_rate > float(gate.max_defect_rate_pct):
                result_status = "failed"
            elif defect_rate > 0:
                result_status = "conditional_pass"
        elif payload.failed_qty > 0:
            result_status = "failed" if defect_rate > 5.0 else "conditional_pass"

        inspection = QualityInspection(
            tenant_id=tenant_id,
            gate_id=payload.gate_id,
            work_order_id=payload.work_order_id,
            po_line_id=payload.po_line_id,
            inspector_id=inspector_id,
            inspected_qty=payload.inspected_qty,
            passed_qty=payload.passed_qty,
            failed_qty=payload.failed_qty,
            defect_reason=payload.defect_reason,
            result=result_status,
        )
        db.add(inspection)
        await db.flush()

        # If units failed, create scrap log
        if payload.failed_qty > 0:
            unit_cost = 5.00  # Default baseline component/WIP cost
            scrap = ScrapLog(
                tenant_id=tenant_id,
                inspection_id=inspection.id,
                qty_scrapped=payload.failed_qty,
                unit_cost=unit_cost,
                total_scrap_cost=round(payload.failed_qty * unit_cost, 2),
                disposition=payload.disposition or "scrap",
                notes=payload.defect_reason,
            )
            db.add(scrap)

        await db.commit()
        await db.refresh(inspection)
        return inspection

    @staticmethod
    async def list_inspections(db: AsyncSession) -> List[QualityInspection]:
        res = await db.execute(select(QualityInspection).order_by(QualityInspection.inspected_at.desc()))
        return res.scalars().all()
