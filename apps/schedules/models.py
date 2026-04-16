from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import BaseModel


class Schedule(BaseModel):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Lunes"
        TUESDAY = 1, "Martes"
        WEDNESDAY = 2, "Miércoles"
        THURSDAY = 3, "Jueves"
        FRIDAY = 4, "Viernes"
        SATURDAY = 5, "Sábado"
        SUNDAY = 6, "Domingo"

    monitor = models.ForeignKey("monitors.Monitor", on_delete=models.CASCADE, related_name="schedules")
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("monitor__full_name", "weekday")
        constraints = [
            models.UniqueConstraint(
                fields=("monitor", "weekday", "start_time", "end_time"),
                name="schedules_unique_monitor_weekday_time_range",
            ),
        ]

    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError("La hora fin debe ser posterior a la hora inicio.")

    def __str__(self) -> str:
        return f"{self.monitor.full_name} - {self.get_weekday_display()}"
