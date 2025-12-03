__copyright__ = 'Copyright 2025 The AMOS Projects'
__author__ = 'ashiven'
__license__ = 'MIT'

import re

from django.forms import ModelForm, PasswordInput
from django.core.exceptions import ValidationError
from workers.models import Configuration


class ConfigurationForm(ModelForm):
    class Meta:
        model = Configuration
        fields = ['name', 'ssh_user', 'ssh_password', 'ip_range']
        widgets = {
            'ssh_password': PasswordInput(),
        }

    def clean_ip_range(self):
        import ipaddress
        ip_range = self.cleaned_data.get('ip_range')
        try:
            ipaddress.IPv4Network(ip_range)
        except (ValueError, ipaddress.NetmaskValueError):
            raise ValidationError("Invalid IP range format. Use CIDR notation (e.g., 192.168.1.0/24)")
        return ip_range
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not re.match(r'^[\w-]+$', name):
            raise ValidationError("Name can only contain letters, numbers, underscores, and hyphens.")
        return name
    
    def clean_ssh_user(self):
        ssh_user = self.cleaned_data.get('ssh_user')
        if not re.match(r'^[\w-]+$', ssh_user):
            raise ValidationError("SSH User can only contain letters, numbers, underscores, and hyphens.")
        return ssh_user
    
    def clean_ssh_password(self):
        ssh_password = self.cleaned_data.get('ssh_password')
        if not re.match(r'^[\w@#$%^&+=!(){}\[\]\-|\\]+$', ssh_password):
            raise ValidationError("SSH Password contains invalid characters. Probably you used a space or quotes.")
        return ssh_password
