from django import template
from django.forms.fields import CheckboxInput

register = template.Library()


@register.filter(name='is_checkbox')
def is_checkbox(value):
    return isinstance(value, CheckboxInput)
