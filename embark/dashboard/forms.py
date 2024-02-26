__copyright__ = 'Copyright 2022-2024 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'

import logging
from django import forms

from uploader.models import FirmwareAnalysis

logger = logging.getLogger(__name__)


class StopAnalysisForm(forms.Form):
    analysis = forms.ModelChoiceField(queryset=FirmwareAnalysis.objects, empty_label='Select Analysis to stop')
