from rest_framework import serializers

from apps.annotations.models import Annotation
from apps.annotations.services import create_annotation


class AnnotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Annotation
        fields = (
            "id",
            "leader",
            "monitor",
            "session",
            "department",
            "annotation_type",
            "description",
            "action",
            "delta_minutes",
            "occurred_on",
            "created_at",
        )
        read_only_fields = ("id", "leader", "department", "created_at")

    def create(self, validated_data):
        request = self.context["request"]
        return create_annotation(leader=request.user, **validated_data)

