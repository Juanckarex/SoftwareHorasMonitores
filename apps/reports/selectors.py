from __future__ import annotations

from datetime import date
from typing import Optional

from django.db.models import Case, Count, IntegerField, Q, Sum, Value, When
from django.db.models.functions import Coalesce

from apps.annotations.models import Annotation
from apps.attendance.selectors import raw_history_for_user
from apps.common.choices import OvertimeStatusChoices, UserRoleChoices
from apps.monitors.selectors import active_monitor_by_code_and_department, visible_monitors_for_user
from apps.notifications.selectors import visible_notifications_for_user
from apps.work_sessions.models import WorkSession
import math

MEMORANDUM_THRESHOLD = 3


def _minutes_to_hours(value) -> str:
    hours = float(value or 0) / 60
    formatted = "{0:.2f}".format(hours).rstrip("0").rstrip(".")
    return formatted or "0"


def _base_session_queryset(*, monitor=None, start_date: Optional[date] = None, end_date: Optional[date] = None):
    queryset = WorkSession.objects.select_related("monitor")
    if monitor is not None:
        queryset = queryset.filter(monitor=monitor)
    if start_date:
        queryset = queryset.filter(work_day__gte=start_date)
    if end_date:
        queryset = queryset.filter(work_day__lte=end_date)
    return queryset


def _base_annotation_queryset(*, monitor=None, start_date: Optional[date] = None, end_date: Optional[date] = None):
    queryset = Annotation.objects.select_related("monitor", "leader")
    if monitor is not None:
        queryset = queryset.filter(monitor=monitor)
    if start_date:
        queryset = queryset.filter(occurred_on__gte=start_date)
    if end_date:
        queryset = queryset.filter(occurred_on__lte=end_date)
    return queryset


def aggregate_monitor_metrics(*, monitor, start_date: Optional[date] = None, end_date: Optional[date] = None) -> dict:
    sessions = _base_session_queryset(monitor=monitor, start_date=start_date, end_date=end_date)
    annotations = _base_annotation_queryset(monitor=monitor, start_date=start_date, end_date=end_date)
    session_totals = sessions.aggregate(
        normal_minutes=(Coalesce(Sum("normal_minutes"), 0)), ##### REDONDEAR HORAS
        approved_overtime_minutes=Coalesce(
            Sum(
                Case(
                    When(overtime_status=OvertimeStatusChoices.APPROVED, then="overtime_minutes"),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            ),
            0,
        ),
        pending_overtime_minutes=Coalesce(
            Sum(
                Case(
                    When(overtime_status=OvertimeStatusChoices.PENDING, then="overtime_minutes"),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            ),
            0,
        ),
        penalty_minutes=Coalesce(Sum("penalty_minutes"), 0),
        late_count=Coalesce(Count("id", filter=Q(is_late=True)), 0),
    )
    annotation_delta_minutes = annotations.aggregate(total=Coalesce(Sum("delta_minutes"), 0))["total"]
    total_minutes = (
        session_totals["normal_minutes"]
        + session_totals["approved_overtime_minutes"]
        + annotation_delta_minutes
    )
    total_minutes = total_minutes
    return {
        **session_totals,
        "annotation_delta_minutes": annotation_delta_minutes,
        "total_minutes": total_minutes,
        "has_memorandum": session_totals["late_count"] >= MEMORANDUM_THRESHOLD,
    }


def build_dashboard_context(user) -> dict:
    monitors = visible_monitors_for_user(user).order_by("department", "full_name")
    monitor_rows = []
    for monitor in monitors:
        metrics = aggregate_monitor_metrics(monitor=monitor)
        dashboard_total_minutes = (
            metrics["normal_minutes"]
            + metrics["approved_overtime_minutes"]
            - metrics["penalty_minutes"]
        )
        metrics.update(
            {
                "department": monitor.department,
                "department_label": monitor.get_department_display(),
                "normal_hours": _minutes_to_hours(metrics["normal_minutes"]),
                "approved_overtime_hours": _minutes_to_hours(metrics["approved_overtime_minutes"]),
                "pending_overtime_hours": _minutes_to_hours(metrics["pending_overtime_minutes"]),
                "penalty_hours": _minutes_to_hours(metrics["penalty_minutes"]),
                "total_hours": _minutes_to_hours(dashboard_total_minutes),
            }
        )
        monitor_rows.append({"monitor": monitor, **metrics})
    pending_overtime = (
        WorkSession.objects.select_related("monitor")
        .filter(overtime_status=OvertimeStatusChoices.PENDING)
        .order_by("-work_day")
    )
    if user.role != UserRoleChoices.ADMIN:
        pending_overtime = pending_overtime.filter(monitor__department=user.department)

    recent_raw_records = raw_history_for_user(user)
    notifications = visible_notifications_for_user(user)[:10]

    return {
        "monitor_rows": monitor_rows,
        "pending_overtime": pending_overtime[:20],
        "recent_raw_records": recent_raw_records,
        "notifications": notifications,
    }


def public_monitor_lookup(*, codigo_estudiante: str, department: str):
    monitor = active_monitor_by_code_and_department(codigo_estudiante, department)
    if not monitor:
        return None
    metrics = aggregate_monitor_metrics(monitor=monitor)
    recent_sessions = (
        WorkSession.objects.filter(monitor=monitor)
        .select_related("raw_record")
        .order_by("-work_day", "-actual_start")[:20]
    )
    return {
        "monitor": monitor,
        "metrics": metrics,
        "recent_sessions": recent_sessions,
    }
