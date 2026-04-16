from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse

from apps.common.choices import DepartmentChoices
from apps.schedules.forms import ScheduleImportForm
from apps.schedules.models import Schedule
from apps.schedules.services import import_schedules_from_workbook


class MonitorDepartmentFilter(admin.SimpleListFilter):
    title = "dependencia"
    parameter_name = "department"

    def lookups(self, request, model_admin):
        return DepartmentChoices.choices

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        return queryset.filter(monitor__department=self.value())


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    change_list_template = "admin/schedules/schedule/change_list.html"
    list_display = ("monitor", "weekday", "start_time", "end_time", "is_active")
    list_filter = ("weekday", "is_active", MonitorDepartmentFilter)
    search_fields = ("monitor__full_name", "monitor__codigo_estudiante")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-schedules/",
                self.admin_site.admin_view(self.import_schedules_view),
                name="schedules_schedule_import",
            ),
        ]
        return custom_urls + urls

    def import_schedules_view(self, request: HttpRequest):
        if request.method == "POST":
            form = ScheduleImportForm(request.POST, request.FILES)
            if form.is_valid():
                result = import_schedules_from_workbook(uploaded_file=form.cleaned_data["source_file"])
                messages.success(
                    request,
                    (
                        "Importaci\u00f3n completada. "
                        f"Monitores procesados: {result.processed_monitors}. "
                        f"Horarios creados: {result.created}. "
                        f"Reactivados: {result.reactivated}. "
                        f"Filas ignoradas: {result.skipped_rows}."
                    ),
                )
                if result.missing_monitors:
                    messages.warning(
                        request,
                        "No se encontraron estos monitores: " + ", ".join(result.missing_monitors[:10]),
                    )
                return HttpResponseRedirect(reverse("admin:schedules_schedule_changelist"))
        else:
            form = ScheduleImportForm()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Importar horarios desde Excel",
            "form": form,
        }
        return render(request, "admin/schedules/schedule/import_form.html", context)
