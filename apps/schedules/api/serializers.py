from rest_framework import serializers

from apps.schedules.models import Schedule


class ScheduleSerializer(serializers.ModelSerializer):
    monitor_name = serializers.CharField(source="monitor.full_name", read_only=True)

    class Meta:
        model = Schedule
        fields = (
            "id",
            "monitor",
            "monitor_name",
            "weekday",
            "start_time",
            "end_time",
            "is_active",
        )

