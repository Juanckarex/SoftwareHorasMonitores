from rest_framework import viewsets

from apps.annotations.api.serializers import AnnotationSerializer
from apps.annotations.selectors import visible_annotations_for_user
from apps.common.permissions import IsAdminOrLeader


class AnnotationViewSet(viewsets.ModelViewSet):
    serializer_class = AnnotationSerializer
    permission_classes = [IsAdminOrLeader]

    def get_queryset(self):
        return visible_annotations_for_user(self.request.user)

