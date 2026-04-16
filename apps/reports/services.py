from __future__ import annotations

from django.db import transaction

from apps.common.events import DomainEvent, event_bus
from apps.reports.events import REPORT_GENERATED
from apps.reports.models import MonitorReportSnapshot
from apps.reports.selectors import aggregate_monitor_metrics


@transaction.atomic
def generate_monitor_report(*, monitor, start_date, end_date, generated_by=None) -> MonitorReportSnapshot:
    metrics = aggregate_monitor_metrics(monitor=monitor, start_date=start_date, end_date=end_date)
    snapshot, _ = MonitorReportSnapshot.objects.update_or_create(
        monitor=monitor,
        start_date=start_date,
        end_date=end_date,
        defaults={
            "generated_by": generated_by,
            "department": monitor.department,
            "normal_minutes": metrics["normal_minutes"],
            "approved_overtime_minutes": metrics["approved_overtime_minutes"],
            "pending_overtime_minutes": metrics["pending_overtime_minutes"],
            "penalty_minutes": metrics["penalty_minutes"],
            "late_count": metrics["late_count"],
            "annotation_delta_minutes": metrics["annotation_delta_minutes"],
            "total_minutes": metrics["total_minutes"],
            "has_memorandum": metrics["has_memorandum"],
        },
    )
    event_bus.publish(
        DomainEvent(
            name=REPORT_GENERATED,
            aggregate_id=str(snapshot.id),
            payload={
                "report_id": str(snapshot.id),
                "department": snapshot.department,
                "monitor_id": str(snapshot.monitor_id),
            },
        )
    )
    return snapshot

