from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q

from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.common.models import BaseModel


class User(AbstractUser, BaseModel):
    role = models.CharField(
        max_length=20,
        choices=UserRoleChoices.choices,
        default=UserRoleChoices.LEADER,
        db_index=True,
    )
    department = models.CharField(
        max_length=32,
        choices=DepartmentChoices.choices,
        blank=True,
        null=True,
        db_index=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(role=UserRoleChoices.ADMIN) | Q(department__isnull=False),
                name="users_department_required_for_leader",
            ),
        ]
        ordering = ("username",)

    @property
    def display_name(self) -> str:
        full_name = self.get_full_name().strip()
        return full_name or self.username
