from django.core.exceptions import PermissionDenied
from django.views.generic import FormView, TemplateView

from apps.common.web import AdminOrLeaderRequiredMixin, enforce_public_lookup_limit
from apps.reports.forms import PublicMonitorLookupForm
from apps.reports.selectors import build_dashboard_context, public_monitor_lookup


class LeaderDashboardView(AdminOrLeaderRequiredMixin, TemplateView):
    template_name = "dashboard/leader_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_dashboard_context(self.request.user))
        return context


class PublicMonitorLookupView(FormView):
    template_name = "public/monitor_lookup.html"
    form_class = PublicMonitorLookupForm

    def form_valid(self, form):
        try:
            enforce_public_lookup_limit(self.request)
        except PermissionDenied as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        result = public_monitor_lookup(
            codigo_estudiante=form.cleaned_data["codigo_estudiante"],
            department=form.cleaned_data["department"],
        )
        context = self.get_context_data(form=form, result=result)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("result", None)
        return context
