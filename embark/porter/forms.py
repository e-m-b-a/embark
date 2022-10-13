import logging

from django import forms
from embark.porter.models import LogZipFile

from uploader.models import FirmwareAnalysis, FirmwareFile

logger = logging.getLogger(__name__)


class FirmwareAnalysisImportForm(forms.Form):
    zip_log_file = forms.ModelChoiceField(queryset=LogZipFile.objects.all(), empty_label='Select the zip-file for the import')
    firmware = forms.ModelChoiceField(queryset=FirmwareFile.objects.all(), empty_label='Select Firmware file the analysis is for')
    version = forms.CharField(max_length=127, empty_label='Version', help_text="Firmware version")
    device = forms.ModelMultipleChoiceField(queryset=Device.objects.all(), empty_label='Select device the analysis is for')
    notes = forms.CharField(max_length=127, empty_label='Notes', help_text="Firmware version notes")

class ExportForm(forms.Form):
    analysis = forms.ModelMultipleChoiceField(queryset=FirmwareAnalysis.objects.filter(failed=False, finished=True), empty_label='Select Analysis to export')
    