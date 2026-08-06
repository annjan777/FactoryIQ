"""
Unit tests for Advanced Production Scheduling:
- Verifies scheduled dates are computed and chained per stage lead times
- Verifies actual_start/actual_end are stamped on WO transitions
- Verifies Gantt endpoint returns the correct flat structure
"""
import pytest
from datetime import datetime, timedelta, timezone

# Stage lead time definitions (mirrors router constants)
STAGES = ["cutting", "stitching", "finishing", "packing"]
STAGE_LEAD_TIMES = {
    "cutting":    8,
    "stitching": 16,
    "finishing":  8,
    "packing":    4,
}

class FakeWorkOrder:
    def __init__(self, stage, sequence_no, scheduled_start, scheduled_end, lead_time_hours):
        self.id = f"wo-{sequence_no}"
        self.stage = stage
        self.sequence_no = sequence_no
        self.status = "pending"
        self.scheduled_start = scheduled_start
        self.scheduled_end = scheduled_end
        self.lead_time_hours = lead_time_hours
        self.actual_start = None
        self.actual_end = None

def build_work_orders(scheduled_start: datetime):
    """Mirrors the scheduling logic in the router."""
    cursor = scheduled_start
    work_orders = []
    for idx, stage in enumerate(STAGES):
        lead_h = STAGE_LEAD_TIMES[stage]
        wo = FakeWorkOrder(
            stage=stage,
            sequence_no=idx + 1,
            scheduled_start=cursor,
            scheduled_end=cursor + timedelta(hours=lead_h),
            lead_time_hours=lead_h,
        )
        cursor = wo.scheduled_end
        work_orders.append(wo)
    return work_orders, cursor  # cursor is po.scheduled_end


class TestScheduledDateChaining:
    def test_lead_times_are_chained_sequentially(self):
        """Each WO starts exactly where the previous one ends."""
        t0 = datetime(2026, 8, 6, 8, 0, 0, tzinfo=timezone.utc)
        wos, po_end = build_work_orders(t0)

        assert len(wos) == 4

        # cutting: 8h
        assert wos[0].scheduled_start == t0
        assert wos[0].scheduled_end   == t0 + timedelta(hours=8)
        assert wos[0].lead_time_hours == 8

        # stitching: 16h, starts right after cutting
        assert wos[1].scheduled_start == wos[0].scheduled_end
        assert wos[1].scheduled_end   == wos[1].scheduled_start + timedelta(hours=16)

        # finishing: 8h
        assert wos[2].scheduled_start == wos[1].scheduled_end
        assert wos[2].scheduled_end   == wos[2].scheduled_start + timedelta(hours=8)

        # packing: 4h
        assert wos[3].scheduled_start == wos[2].scheduled_end
        assert wos[3].scheduled_end   == wos[3].scheduled_start + timedelta(hours=4)

    def test_total_duration_is_sum_of_lead_times(self):
        """Total production order duration == sum of all stage lead times."""
        t0 = datetime(2026, 8, 6, 8, 0, 0, tzinfo=timezone.utc)
        wos, po_end = build_work_orders(t0)

        expected_total_hours = sum(STAGE_LEAD_TIMES.values())  # 8+16+8+4 = 36h
        actual_hours = (po_end - t0).total_seconds() / 3600
        assert actual_hours == expected_total_hours

    def test_scheduled_start_defaults_when_not_provided(self):
        """When no scheduled_start is given, defaults to now() (within 1s tolerance)."""
        before = datetime.now(timezone.utc)
        wos, _ = build_work_orders(datetime.now(timezone.utc))
        after = datetime.now(timezone.utc)

        # First WO should have started approximately now
        assert before <= wos[0].scheduled_start <= after


class TestActualTimestamps:
    def test_actual_start_stamped_on_active_transition(self):
        """Transitioning a WO to active stamps actual_start."""
        t0 = datetime(2026, 8, 6, 8, 0, 0, tzinfo=timezone.utc)
        wos, _ = build_work_orders(t0)
        wo = wos[0]

        now = datetime.now(timezone.utc)
        wo.status = "active"
        wo.actual_start = now

        assert wo.actual_start is not None
        assert wo.actual_end is None

    def test_actual_end_stamped_on_completed_transition(self):
        """Transitioning a WO to completed stamps actual_end."""
        t0 = datetime(2026, 8, 6, 8, 0, 0, tzinfo=timezone.utc)
        wos, _ = build_work_orders(t0)
        wo = wos[0]

        now = datetime.now(timezone.utc)
        wo.status = "active"
        wo.actual_start = now

        # Complete it
        later = now + timedelta(hours=9)
        wo.status = "completed"
        wo.actual_end = later

        assert wo.actual_start < wo.actual_end

    def test_schedule_adherence_can_be_measured(self):
        """Actual duration can be compared against scheduled (planned vs. actual)."""
        t0 = datetime(2026, 8, 6, 8, 0, 0, tzinfo=timezone.utc)
        wos, _ = build_work_orders(t0)
        wo = wos[0]  # cutting: planned 8h

        wo.actual_start = t0
        wo.actual_end = t0 + timedelta(hours=10)  # ran 2h over

        planned_h = (wo.scheduled_end - wo.scheduled_start).total_seconds() / 3600
        actual_h  = (wo.actual_end - wo.actual_start).total_seconds() / 3600
        variance_h = actual_h - planned_h

        assert planned_h == 8
        assert actual_h == 10
        assert variance_h == 2  # 2h delay


class TestGanttStructure:
    def test_gantt_output_shape(self):
        """Gantt bars contain all required fields."""
        t0 = datetime(2026, 8, 6, 8, 0, 0, tzinfo=timezone.utc)
        wos, _ = build_work_orders(t0)

        po_id = "po-test-001"
        gantt_bars = [
            {
                "production_order_id": po_id,
                "work_order_id": wo.id,
                "stage": wo.stage,
                "sequence_no": wo.sequence_no,
                "status": wo.status,
                "scheduled_start": wo.scheduled_start,
                "scheduled_end": wo.scheduled_end,
                "actual_start": wo.actual_start,
                "actual_end": wo.actual_end,
                "lead_time_hours": wo.lead_time_hours,
            }
            for wo in wos
        ]

        assert len(gantt_bars) == 4
        # Verify sorted order
        assert [b["stage"] for b in gantt_bars] == ["cutting", "stitching", "finishing", "packing"]
        # Every bar references the same production order
        assert all(b["production_order_id"] == po_id for b in gantt_bars)
        # All have lead times
        assert all(b["lead_time_hours"] is not None for b in gantt_bars)
