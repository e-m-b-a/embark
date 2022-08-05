# pylint: disable=E1101
import logging
import django
from django import forms

from uploader import models

logger = logging.getLogger(__name__)


class FirmwareAnalysisForm(forms.ModelForm):

    class Meta:
        model = models.FirmwareAnalysis

        fields = ('firmware', 'version', 'vendor', 'device', 'notes', 'firmware_Architecture', 'cwe_checker', 'deep_extraction', 'online_checks', 
                 # 'dev_mode',  'dependency_check', 'multi_threaded', 'firmware_remove', 'log_path', 'grep_able_log', 'relative_paths', 'ANSI_color',
                  'web_reporter', 'user_emulation_test', 'system_emulation_test',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.visible_fields():

            if isinstance(field.field.widget, django.forms.widgets.TextInput):
                field.field.widget.attrs['class'] = 'form-control formTxtField'
                field.field.widget.attrs['placeholder'] = field.label

            if isinstance(field.field.widget, django.forms.widgets.CheckboxInput):
                field.field.widget.attrs['class'] = 'form-check-input active'

            if isinstance(field.field.widget, django.forms.widgets.Select):
                field.field.widget.attrs['class'] = 'form-control select dropdownSelect'

            # TODO work to get rid of
            try:
                if field.field.readonly:
                    field.field.widget.attrs["disabled"] = "disabled"
            except Exception as error:
                logger.info("Exception passed: %s", error)
                # pass

            try:
                field.expert_mode = field.field.expert_mode
            except Exception as error:
                logger.info("Exception passed: %s", error)
                # pass

        self.base_fields['firmware'] = forms.ModelChoiceField(queryset=models.FirmwareFile.objects, empty_label='Select firmware')


class DeleteFirmwareForm(forms.Form):
    firmware = forms.ModelChoiceField(queryset=models.FirmwareFile.objects, empty_label='Select firmware-file to delete')
