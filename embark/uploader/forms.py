import django
from django import forms

from uploader import models


class FirmwareForm(forms.ModelForm):

    class Meta:
        model = models.Firmware

        fields = ('firmware', 'version', 'vendor', 'device', 'notes', 'firmware_Architecture', 'cwe_checker',
                  'docker_container', 'deep_extraction', 'log_path', 'grep_able_log', 'relative_paths', 'ANSI_color',
                  'web_reporter', 'emulation_test', 'dependency_check', 'multi_threaded')

    def __init__(self, *args, **kwargs):

        super(FirmwareForm, self).__init__(*args, **kwargs)

        for field in self.visible_fields():

            if isinstance(field.field.widget, django.forms.widgets.TextInput):
                field.field.widget.attrs['class'] = 'form-control formTxtField'
                field.field.widget.attrs['placeholder'] = field.label

            if isinstance(field.field.widget, django.forms.widgets.CheckboxInput):
                field.field.widget.attrs['class'] = 'form-check-input active'

            if isinstance(field.field.widget, django.forms.widgets.Select):
                field.field.widget.attrs['class'] = 'form-control select dropdownSelect'

            try:
                if field.field.readonly:
                    field.field.widget.attrs["disabled"] = "disabled"
            except:
                pass

            try:
                field.expert_mode = field.field.expert_mode
            except:
                pass


class DeleteFirmwareForm(forms.ModelForm):

    class Meta:
        model = models.DeleteFirmware

        fields = ('firmware', )

    def __init__(self, *args, **kwargs):
        super(DeleteFirmwareForm, self).__init__(*args, **kwargs)
