import pytest

from apps.annotations.services import create_annotation
from tests.factories import MonitorFactory, UserFactory


@pytest.mark.django_db
def test_annotation_can_add_or_deduct_minutes():
    leader = UserFactory()
    monitor = MonitorFactory(department=leader.department)

    plus = create_annotation(
        leader=leader,
        monitor=monitor,
        annotation_type="virtual_hours",
        description="Se ajusta una sesión virtual.",
        action="add",
        delta_minutes=45,
        occurred_on="2026-04-13",
    )
    minus = create_annotation(
        leader=leader,
        monitor=monitor,
        annotation_type="permission",
        description="Descuento por permiso.",
        action="deduct",
        delta_minutes=-30,
        occurred_on="2026-04-13",
    )

    assert plus.delta_minutes == 45
    assert minus.delta_minutes == -30

