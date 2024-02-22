import logging
from django import forms

from uploader.models import FirmwareAnalysis, Label

logger = logging.getLogger(__name__)


class StopAnalysisForm(forms.Form):
    analysis = forms.ModelChoiceField(queryset=FirmwareAnalysis.objects, empty_label='Select Analysis to stop')


class LabelSelectForm(forms.Form):
    label = forms.ModelChoiceField(queryset=Label.objects.all(), empty_label='Select Label to add')
