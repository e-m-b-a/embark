__copyright__ = 'Copyright 2025 Siemens Energy AG, Copyright 2025 The AMOS Projects'
__author__ = 'ashiven'
__license__ = 'MIT'

import re

from django.forms import ModelForm
from django.core.exceptions import ValidationError
from workers.models import Configuration


class ConfigurationForm(ModelForm):
    class Meta:
        model = Configuration
        fields = ['name', 'ssh_user', 'ssh_password', 'ip_range']

    def clean_ip_range(self):
        ip_range = self.cleaned_data.get('ip_range')
        ip_range_regex = r"^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$"
        if not re.match(ip_range_regex, ip_range):
            raise ValidationError("Invalid IP range format. Use CIDR notation")
        return ip_range
