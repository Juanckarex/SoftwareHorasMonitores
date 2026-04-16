from typing import Optional

from datetime import date

from apps.schedules.models import Schedule
from apps.common.utils import overlap_in_minutes


def schedule_for_monitor_and_day(monitor, day: date, start_time=None, end_time=None) -> Optional[Schedule]:
    schedules = list(
        Schedule.objects.filter(
            monitor=monitor,
            weekday=day.weekday(),
            is_active=True,
        ).order_by("start_time")
    )
    if not schedules:
        return None
    if start_time is None or end_time is None:
        return schedules[0]

    best_schedule = None
    best_overlap = 0
    for schedule in schedules:
        overlap = overlap_in_minutes(start_time, end_time, schedule.start_time, schedule.end_time)
        if overlap > best_overlap:
            best_schedule = schedule
            best_overlap = overlap
    return best_schedule if best_overlap > 0 else None
