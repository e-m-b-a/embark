import logging

from django import forms

from porter.models import LogZipFile
from uploader.models import FirmwareAnalysis, FirmwareFile, Device

logger = logging.getLogger(__name__)


class FirmwareAnalysisImportForm(forms.Form):
    zip_log_file = forms.ModelChoiceField(queryset=LogZipFile.objects.all(), empty_label='Select the zip-file for the import', required=True)
    firmware = forms.ModelChoiceField(queryset=FirmwareFile.objects.all(), empty_label='Select Firmware file the analysis is for', required=False)
    device = forms.ModelMultipleChoiceField(queryset=Device.objects.all(), required=False, widget=forms.CheckboxSelectMultiple)

    version = forms.CharField(max_length=127, help_text="Firmware version", required=False)
    notes = forms.CharField(max_length=127, help_text="Firmware version notes", required=False)


class FirmwareAnalysisExportForm(forms.Form):
    analysis = forms.ModelChoiceField(queryset=FirmwareAnalysis.objects.filter(finished=True, failed=False))
