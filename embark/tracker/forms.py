import logging

from django import forms

from uploader.models import Device


logger = logging.getLogger(__name__)


class DateInput(forms.DateInput):

    input_type = 'date'


class TimeForm(forms.Form):

    date = forms.DateField(widget=DateInput())


class AssociateForm(forms.Form):
    device = forms.ModelChoiceField(queryset=Device.objects.all())
