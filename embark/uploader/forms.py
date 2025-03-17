# pylint: disable=E1101
__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'Benedikt Kuehne, Maximilian Wagner, m-1-k-3, VAISHNAVI UMESH, diegiesskanne'
__license__ = 'MIT'

import logging

from django.conf import settings
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

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('device_name')
        vendor = cleaned_data.get('device_vendor')
        if name and vendor:
            if models.Device.objects.filter(device_name=name, device_vendor=vendor).exists():
                self.add_error('device_name', 'device already created')
        return cleaned_data


class FirmwareAnalysisForm(forms.ModelForm):
    MODULE_CHOICES = settings.EMBA_MODULE_DICT['F_Modules'] + settings.EMBA_MODULE_DICT['L_Modules'] + settings.EMBA_MODULE_DICT['P_Modules'] + settings.EMBA_MODULE_DICT['S_Modules'] + settings.EMBA_MODULE_DICT['Q_Modules']
    scan_modules = forms.MultipleChoiceField(choices=MODULE_CHOICES, help_text='Enable/disable specific scan-modules for your analysis', widget=forms.CheckboxSelectMultiple, required=False)

    class Meta:
        model = models.FirmwareAnalysis

        fields = ['firmware', 'version', 'device', 'notes', 'firmware_Architecture', 'user_emulation_test', 'system_emulation_test', 'sbom_only_test', 'scan_modules']
        widgets = {
            "device": forms.CheckboxSelectMultiple,
        }

    def clean_scan_modules(self):
        logger.debug("starting the cleaning")
        _scan_modules = self.cleaned_data.get('scan_modules') or None
        logger.debug("got modules : %s", _scan_modules)
        return _scan_modules


class DeleteFirmwareForm(forms.Form):
    firmware = forms.ModelChoiceField(queryset=models.FirmwareFile.objects, empty_label='Select firmware-file to delete')
