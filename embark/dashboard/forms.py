import logging
from django import forms

from uploader.models import FirmwareAnalysis

logger = logging.getLogger('web')

class StopAnalysisForm(forms.Form):
    firmware = forms.ModelChoiceField(queryset=FirmwareAnalysis.objects, empty_label='Select Analysis to stop')
