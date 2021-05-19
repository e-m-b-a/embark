import logging

import django
from django import forms, template
from django.forms import CheckboxInput

from uploader import models


class FirmwareForm(forms.ModelForm):

    class Meta:
        model = models.Firmware

        fields = ('version', 'vendor', 'device', 'notes', 'firmware_Architecture', 'cwe_checker',
                  'docker_container', 'deep_extraction', 'log_path', 'grep_able_log', 'relative_paths', 'ANSI_color',
                  'web_reporter', 'emulation_test')

    def __init__(self, *args, **kwargs):

        super(FirmwareForm, self).__init__(*args, **kwargs)

        for field in self.visible_fields():
            if isinstance(field.field.widget, django.forms.widgets.TextInput):
                field.field.widget.attrs['class'] = 'form-control txtField'

            if isinstance(field.field.widget, django.forms.widgets.CheckboxInput):
                field.field.widget.attrs['class'] = 'form-check-input active'

            if isinstance(field.field, models.BooleanFieldExpertModeForm):
                field.expert_mode = field.field.expert_mode
                field.required = False
