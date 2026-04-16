from rest_framework.routers import SimpleRouter

from apps.schedules.api.views import ScheduleViewSet

router = SimpleRouter()
router.register("", ScheduleViewSet, basename="schedule")

urlpatterns = router.urls
