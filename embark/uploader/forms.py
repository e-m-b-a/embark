# pylint: disable=E1101
import logging
from django import forms

from uploader import models

logger = logging.getLogger(__name__)


class VendorForm(forms.ModelForm):

    class Meta:
        model = models.Vendor

        fields = ['vendor_name']


class LabelForm(forms.ModelForm):

    class Meta:
        model = models.Label

        fields = ['label_name']


class DeviceForm(forms.ModelForm):

    class Meta:
        model = models.Device

        fields = ['device_name', 'device_label', 'device_vendor']


class FirmwareAnalysisForm(forms.ModelForm):

    class Meta:
        model = models.FirmwareAnalysis

        fields = ['firmware', 'version', 'device', 'notes', 'firmware_Architecture', 'user_emulation_test', 'system_emulation_test', 'scan_modules']
        widgets = {
            "device": forms.CheckboxSelectMultiple,
            "scan_modules": forms.CheckboxSelectMultiple
        }
    def clean(self):
        try:
            super().clean
        except forms.ValidationError as error:
          logger.error("Validation error in clean: %s", error)

    def clean_scan_modules(self):
        logger.debug("starting the cleaning")
        _scan_modules = self.cleaned_data.get('scan_modules') or None
        logger.debug("got modules : %s", _scan_modules)
        return _scan_modules


class DeleteFirmwareForm(forms.Form):
    firmware = forms.ModelChoiceField(queryset=models.FirmwareFile.objects, empty_label='Select firmware-file to delete')
