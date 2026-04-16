from datetime import date, datetime, time

import pytest

from apps.attendance.services import create_import_job, import_workbook
from apps.attendance.models import AttendanceRawRecord
from apps.common.choices import OvertimeStatusChoices, ReconciliationStatusChoices
from apps.schedules.services import upsert_schedule
from apps.work_sessions.models import WorkSession
from tests.conftest import build_excel_file
from tests.factories import MonitorFactory, UserFactory


@pytest.mark.django_db
def test_import_workbook_matches_monitor_and_creates_session(sample_excel_file):
    uploader = UserFactory()
    monitor = MonitorFactory(full_name="Ana Torres")
    upsert_schedule(monitor=monitor, weekday=0, start_time=time(hour=8), end_time=time(hour=12))

    job = create_import_job(uploaded_file=sample_excel_file, uploaded_by=uploader)
    import_workbook(job)

    raw_record = job.raw_records.get()
    session = raw_record.work_session

    assert job.status == "completed"
    assert raw_record.reconciliation_status == ReconciliationStatusChoices.MATCHED
    assert raw_record.monitor == monitor
    assert session.normal_minutes == 240
    assert session.overtime_minutes == 30
    assert session.overtime_status == OvertimeStatusChoices.PENDING


@pytest.mark.django_db
def test_import_workbook_leaves_unmatched_record_pending_manual_review():
    uploader = UserFactory()
    excel_file = build_excel_file(
        headers=["Nombre", "Departamento", "Fecha", "Hora Entrada", "Hora Salida"],
        rows=[["Persona Inexistente", "Física", "2026-04-13", "08:00", "12:00"]],
    )

    job = create_import_job(uploaded_file=excel_file, uploaded_by=uploader)
    import_workbook(job)

    raw_record = job.raw_records.get()

    assert raw_record.reconciliation_status == ReconciliationStatusChoices.MANUAL_REVIEW
    assert not hasattr(raw_record, "work_session")


@pytest.mark.django_db
def test_import_workbook_skips_duplicate_rows_from_reimport():
    uploader = UserFactory()
    monitor = MonitorFactory(full_name="Ana Torres")
    upsert_schedule(monitor=monitor, weekday=0, start_time=time(hour=8), end_time=time(hour=12))

    headers = [
        "departamento",
        "nro._usuario",
        "id_de_usuario",
        "nombre",
        "fecha_inicio",
        "fecha_fin",
        "descripci\u00f3n_de_la_excepci\u00f3n",
        "tiempo_trabajado",
        "d\u00edas_de_trabajo",
        "tiempo_de_trabajo",
        "observaciones",
    ]
    rows = [[
        "Fisica",
        "2001",
        "1050",
        "Ana Torres",
        datetime(2026, 4, 13, 8, 0),
        datetime(2026, 4, 13, 12, 30),
        "Overtime",
        "04:30:00",
        1,
        "04:30:00",
        "",
    ]]

    first_job = create_import_job(uploaded_file=build_excel_file(headers=headers, rows=rows), uploaded_by=uploader)
    import_workbook(first_job)

    second_job = create_import_job(uploaded_file=build_excel_file(headers=headers, rows=rows), uploaded_by=uploader)
    import_workbook(second_job)

    raw_records = AttendanceRawRecord.objects.filter(
        normalized_full_name=monitor.normalized_full_name,
        work_day=date(2026, 4, 13),
        entry_at=time(hour=8),
        exit_at=time(hour=12, minute=30),
    )
    sessions = WorkSession.objects.filter(
        monitor=monitor,
        work_day=date(2026, 4, 13),
        actual_start=time(hour=8),
        actual_end=time(hour=12, minute=30),
    )

    assert first_job.imported_rows == 1
    assert second_job.imported_rows == 0
    assert second_job.failed_rows == 0
    assert raw_records.count() == 1
    assert sessions.count() == 1
