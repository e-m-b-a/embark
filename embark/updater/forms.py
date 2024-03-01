import logging
from django import forms

logger = logging.getLogger(__name__)


class EmbaUpdateForm(forms.Form):
    option = forms.ChoiceField(choices=[
        (0, 'Git Update'), (1, 'Docker Update')
    ], help_text='Update EMBA', widget=forms.CheckboxSelectMultiple, required=True)


class CheckForm(forms.Form):
    option = forms.ChoiceField(choices=[
        (1, 'Host and container'), (2, 'Only Container')
    ], help_text='Check EMBA', widget=forms.CheckboxSelectMultiple, required=True)
