from django import forms

from apps.attendance.validators import validate_excel_extension


class ScheduleImportForm(forms.Form):
    source_file = forms.FileField(label="Archivo de horarios")

    def clean_source_file(self):
        source_file = self.cleaned_data["source_file"]
        validate_excel_extension(source_file.name)
        return source_file
