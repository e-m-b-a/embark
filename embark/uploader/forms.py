# pylint: disable=E1101
import logging
from tkinter import Widget
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

        fields = ['firmware', 'version', 'device', 'notes', 'firmware_Architecture', 'cwe_checker', 'deep_extraction', 'online_checks', 'user_emulation_test', 'system_emulation_test']
        widgets = {
            "device": forms.CheckboxSelectMultiple
        }


class DeleteFirmwareForm(forms.Form):
    firmware = forms.ModelChoiceField(queryset=models.FirmwareFile.objects, empty_label='Select firmware-file to delete')
