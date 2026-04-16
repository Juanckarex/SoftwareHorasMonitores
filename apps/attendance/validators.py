from datetime import date, datetime, time
from pathlib import Path
from typing import Dict, List, Optional

from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_date, parse_datetime, parse_time

SUPPORTED_EXTENSIONS = {".xlsx", ".xlsm"}
HEADER_ALIASES = {
    "departamento": "department",
    "nro._usuario": "num_user",
    "id_de_usuario": "id_user",
    "nombre": "full_name",
    "fecha_inicio": "entry_at",
    "fecha_fin": "exit_at",
    "descripción_de_la_excepción": "description",
    "tiempo_trabajado": "worked_time",
    "días_de_trabajo": "days_worked",
    "tiempo_de_trabajo": "working_time",
    "observaciones": "observations",
}


def validate_excel_extension(file_name: str) -> None:
    if Path(file_name).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValidationError("Solo se permiten archivos Excel .xlsx o .xlsm.")


def normalize_header(value: str) -> str:
    return " ".join((value or "").strip().lower().replace(" ", "_").split())


def resolve_headers(headers: List[str]) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for index, header in enumerate(headers):
        # print(f"{header} : {normalize_header(str(header))}")
        alias = HEADER_ALIASES.get(normalize_header(str(header)))
        if alias and alias not in mapping:
            mapping[alias] = index
    missing = {"department", "num_user", "id_user", "full_name", "entry_at", "exit_at", "description", "worked_time", "days_worked", "working_time", "observations"} - set(mapping)
    if missing:
        raise ValidationError(f"Encabezados faltantes en el Excel: {', '.join(sorted(missing))}.")
    return mapping


def coerce_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = parse_date(str(value))
    if parsed is None:
        raise ValidationError("No fue posible interpretar la fecha del registro.")
    return parsed


def coerce_time(value) -> time:
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value
    parsed = parse_time(str(value))
    if parsed is None:
        raise ValidationError("No fue posible interpretar la hora del registro.")
    return parsed


def coerce_datetime(value, fallback_date: Optional[date] = None) -> datetime:
    if isinstance(value, datetime):
        return value
    parsed = parse_datetime(str(value))
    if parsed:
        return parsed
    if fallback_date is not None:
        return datetime.combine(fallback_date, coerce_time(value))
    raise ValidationError("No fue posible interpretar la fecha y hora del registro.")
