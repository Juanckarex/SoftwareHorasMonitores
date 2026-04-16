from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.cache import cache
from django.core.exceptions import PermissionDenied

from apps.common.choices import UserRoleChoices


class AdminOrLeaderRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_active and user.role in {
            UserRoleChoices.ADMIN,
            UserRoleChoices.LEADER,
        }


def enforce_public_lookup_limit(request, limit: int | None = None, window_seconds: int | None = None) -> None:
    limit = limit if limit is not None else getattr(settings, "PUBLIC_LOOKUP_LIMIT", 10)
    window_seconds = (
        window_seconds
        if window_seconds is not None
        else getattr(settings, "PUBLIC_LOOKUP_WINDOW_SECONDS", 3600)
    )
    client_ip = request.META.get("REMOTE_ADDR", "anonymous")
    cache_key = "public_lookup:{0}".format(client_ip)
    current = cache.get(cache_key, 0)
    if current >= limit:
        raise PermissionDenied("Se alcanzó el límite de consultas por hora.")
    cache.set(cache_key, current + 1, timeout=window_seconds)
