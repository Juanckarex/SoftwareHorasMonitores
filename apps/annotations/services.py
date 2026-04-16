from django.core.exceptions import ValidationError

from apps.annotations.events import ANNOTATION_CREATED
from apps.annotations.models import Annotation
from apps.common.events import DomainEvent, event_bus
from apps.common.permissions import department_allowed


def create_annotation(
    *,
    leader,
    monitor,
    annotation_type: str,
    description: str,
    action: str,
    delta_minutes: int,
    occurred_on,
    session=None,
) -> Annotation:
    if not department_allowed(leader, monitor.department):
        raise ValidationError("No puedes anotar monitores de otra dependencia.")
    annotation = Annotation(
        leader=leader,
        monitor=monitor,
        session=session,
        department=monitor.department,
        annotation_type=annotation_type,
        description=description,
        action=action,
        delta_minutes=delta_minutes,
        occurred_on=occurred_on,
    )
    annotation.full_clean()
    annotation.save()
    event_bus.publish(
        DomainEvent(
            name=ANNOTATION_CREATED,
            aggregate_id=str(annotation.id),
            payload={
                "annotation_id": str(annotation.id),
                "department": annotation.department,
                "monitor_id": str(annotation.monitor_id),
            },
        )
    )
    return annotation
