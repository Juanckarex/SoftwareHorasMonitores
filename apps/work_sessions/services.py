from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.common.choices import OvertimeStatusChoices, SessionStateChoices, UserRoleChoices
from apps.common.events import DomainEvent, event_bus
from apps.common.permissions import department_allowed
from apps.common.utils import (
    combine_day_and_time,
    duration_between_times,
    duration_in_minutes,
    normalize_session_end,
    normalize_session_start,
    overlap_in_minutes,
)
from apps.schedules.selectors import schedule_for_monitor_and_day
from apps.work_sessions.events import OVERTIME_PENDING, OVERTIME_REVIEWED, SESSION_PROCESSED
from apps.work_sessions.models import WorkSession


@transaction.atomic
def process_raw_record_to_session(*, raw_record):
    try:
        return raw_record.work_session
    except WorkSession.DoesNotExist:
        pass
    if not raw_record.is_processable:
        raise ValidationError("El registro crudo no es procesable.")

    normalized_start = normalize_session_start(raw_record.entry_at)
    normalized_end = normalize_session_end(raw_record.exit_at)
    schedule = schedule_for_monitor_and_day(
        raw_record.monitor,
        raw_record.work_day,
        start_time=normalized_start,
        end_time=normalized_end,
    )
    total_minutes = duration_between_times(normalized_start, normalized_end)
    scheduled_start = None
    scheduled_end = None
    normal = 0
    late = 0
    session_state = SessionStateChoices.PROCESSED

    if schedule:
        scheduled_start = combine_day_and_time(raw_record.work_day, schedule.start_time)
        scheduled_end = combine_day_and_time(raw_record.work_day, schedule.end_time)
        normal = overlap_in_minutes(normalized_start, normalized_end, schedule.start_time, schedule.end_time)
        late = max(duration_in_minutes(normalized_start) - duration_in_minutes(schedule.start_time), 0)
    else:
        session_state = SessionStateChoices.WITHOUT_SCHEDULE

    overtime = max(total_minutes - normal, 0)
    overtime_status = (
        OvertimeStatusChoices.PENDING if overtime > 0 else OvertimeStatusChoices.NOT_APPLICABLE
    )

    session = WorkSession.objects.create(
        raw_record=raw_record,
        monitor=raw_record.monitor,
        schedule=schedule,
        work_day=raw_record.work_day,
        actual_start=raw_record.entry_at,
        actual_end=raw_record.exit_at,
        normalized_start=normalized_start,
        normalized_end=normalized_end,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        normal_minutes=normal,
        overtime_minutes=overtime,
        late_minutes=late,
        is_late=late > 0,
        session_state=session_state,
        overtime_status=overtime_status,
    )

    raw_record.processed_at = timezone.now()
    raw_record.processing_error = ""
    raw_record.save(update_fields=["processed_at", "processing_error", "updated_at"])

    event_bus.publish(
        DomainEvent(
            name=SESSION_PROCESSED,
            aggregate_id=str(session.id),
            payload={
                "session_id": str(session.id),
                "monitor_id": str(session.monitor_id),
                "overtime_minutes": session.overtime_minutes,
            },
        )
    )
    if session.overtime_status == OvertimeStatusChoices.PENDING:
        event_bus.publish(
            DomainEvent(
                name=OVERTIME_PENDING,
                aggregate_id=str(session.id),
                payload={
                    "session_id": str(session.id),
                    "monitor_id": str(session.monitor_id),
                    "department": session.monitor.department,
                    "overtime_minutes": session.overtime_minutes,
                },
            )
        )
    return session


@transaction.atomic
def review_overtime(*, session: WorkSession, reviewer, decision: str, note: str = "") -> WorkSession:
    if reviewer.role not in {UserRoleChoices.ADMIN, UserRoleChoices.LEADER}:
        raise ValidationError("Solo administradores o líderes pueden revisar horas extra.")
    if not department_allowed(reviewer, session.monitor.department):
        raise ValidationError("No puedes revisar sesiones de otra dependencia.")
    if session.overtime_status != OvertimeStatusChoices.PENDING:
        raise ValidationError("La sesión no tiene horas extra pendientes.")

    note = (note or "").strip()
    if decision == "approve":
        session.overtime_status = OvertimeStatusChoices.APPROVED
        session.penalty_minutes = 0
    elif decision == "reject":
        if not note:
            raise ValidationError("Rechazar horas extra requiere una anotación obligatoria.")
        session.overtime_status = OvertimeStatusChoices.REJECTED
        session.penalty_minutes = session.overtime_minutes
        from apps.annotations.services import create_annotation

        create_annotation(
            leader=reviewer,
            monitor=session.monitor,
            session=session,
            annotation_type="novelty",
            description=note,
            action="deduct",
            delta_minutes=-session.overtime_minutes,
            occurred_on=session.work_day,
        )
    else:
        raise ValidationError("Decisión inválida.")

    session.overtime_reviewed_by = reviewer
    session.overtime_reviewed_at = timezone.now()
    session.overtime_review_note = note
    session.save(
        update_fields=[
            "overtime_status",
            "penalty_minutes",
            "overtime_reviewed_by",
            "overtime_reviewed_at",
            "overtime_review_note",
            "updated_at",
        ]
    )

    event_bus.publish(
        DomainEvent(
            name=OVERTIME_REVIEWED,
            aggregate_id=str(session.id),
            payload={
                "session_id": str(session.id),
                "department": session.monitor.department,
                "decision": decision,
            },
        )
    )
    return session
