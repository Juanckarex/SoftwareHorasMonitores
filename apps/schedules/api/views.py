from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from apps.common.choices import UserRoleChoices
from apps.common.permissions import IsAdminOrLeader
from apps.monitors.selectors import visible_monitors_for_user
from apps.schedules.api.serializers import ScheduleSerializer
from apps.schedules.models import Schedule


class ScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = ScheduleSerializer
    queryset = Schedule.objects.select_related("monitor")
    permission_classes = [IsAdminOrLeader]

    def get_queryset(self):
        monitors = visible_monitors_for_user(self.request.user)
        return self.queryset.filter(monitor__in=monitors)

    def perform_create(self, serializer):
        monitor = serializer.validated_data["monitor"]
        if self.request.user.role != UserRoleChoices.ADMIN and monitor.department != self.request.user.department:
            raise PermissionDenied("No puedes crear horarios para otra dependencia.")
        serializer.save()

    def perform_update(self, serializer):
        monitor = serializer.instance.monitor
        if self.request.user.role != UserRoleChoices.ADMIN and monitor.department != self.request.user.department:
            raise PermissionDenied("No puedes editar horarios de otra dependencia.")
        serializer.save()
