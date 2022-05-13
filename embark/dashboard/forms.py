import logging
from django import forms

logger = logging.getLogger('web')

class StopAnalysisForm(forms.Form):
    id = forms.UUIDField
