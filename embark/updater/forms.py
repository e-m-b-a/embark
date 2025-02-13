__copyright__ = 'Copyright 2025 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

import logging
from django import forms

logger = logging.getLogger(__name__)


class EmbaUpdateForm(forms.Form):
    option = forms.MultipleChoiceField(choices=[
        ('GIT', 'Git Update'), ('DOCKER', 'Docker Update'), ('NVD', 'CVE Update')
    ], help_text='Update EMBA', widget=forms.CheckboxSelectMultiple, required=False)


class CheckForm(forms.Form):
    option = forms.ChoiceField(choices=[
        ('BOTH', 'Host and container'), ('CONTAINER', 'Only Container')
    ], help_text='Check EMBA', widget=forms.Select, required=True)
