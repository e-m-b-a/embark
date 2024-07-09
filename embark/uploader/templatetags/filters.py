__copyright__ = 'Copyright 2021-2024 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'Maximilian Wagner'
__license__ = 'MIT'

from django import template
from django.forms.fields import CheckboxInput

register = template.Library()


@register.filter(name='is_checkbox')
def is_checkbox(value):
    return isinstance(value, CheckboxInput)
