import logging
import django
from django import forms

from uploader import models

logger = logging.getLogger('web')


class FirmwareForm(forms.ModelForm):

    class Meta:
        model = models.Firmware

        fields = ('firmware', 'version', 'vendor', 'device', 'notes', 'firmware_Architecture', 'cwe_checker',
                  'dev_mode', 'deep_extraction', 'log_path', 'grep_able_log', 'relative_paths', 'ANSI_color',
                  'web_reporter', 'emulation_test', 'dependency_check', 'multi_threaded', 'firmware_remove')

    def __init__(self, *args, **kwargs):
        # super(FirmwareForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)

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
            except Exception as error:
                logger.info("Exception passed: %s", error)
                # pass

            try:
                field.expert_mode = field.field.expert_mode
            except Exception as error:
                logger.info("Exception passed: %s", error)
                # pass

        self.base_fields['firmware'] = forms.ModelChoiceField(queryset=models.FirmwareFile.objects, empty_label='Select firmware')


class DeleteFirmwareForm(forms.ModelForm):

    class Meta:
        model = models.DeleteFirmware

        fields = ('firmware', )

    def __init__(self, *args, **kwargs):
        # super(DeleteFirmwareForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)
        for field in self.visible_fields():
            if isinstance(field.field.widget, django.forms.widgets.Select):
                field.field.widget.attrs['class'] = 'form-control select dropdownSelect'

        self.base_fields['firmware'] = forms.ModelChoiceField(queryset=models.FirmwareFile.objects, empty_label='Select firmware to delete')
