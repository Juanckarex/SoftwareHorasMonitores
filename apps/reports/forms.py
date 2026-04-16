from django import forms

from apps.common.choices import DepartmentChoices


class PublicMonitorLookupForm(forms.Form):
    codigo_estudiante = forms.CharField(max_length=20, label="Código de estudiante")
    department = forms.ChoiceField(choices=DepartmentChoices.choices, label="Dependencia")

