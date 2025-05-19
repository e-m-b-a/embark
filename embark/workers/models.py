from django.db import models
import ipaddress
from django.core.exceptions import ValidationError

from users.models import Configuration


# TODO: add explicit makemigrations command for workers models in scripts i.e. debug-server-start.sh etc.

class Worker(models.Model):
    configurations = models.ManyToManyField(Configuration, related_name='workers', blank=True)
    name = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(unique=True)
    system_info = models.JSONField()

    def clean(self):
        super().clean()
        if self.configurations.exists():
            for config in self.configurations.all():
                if config.ip_range:
                    try:
                        network = ipaddress.ip_network(config.ip_range, strict=False)
                        ip = ipaddress.ip_address(self.ip_address)
                        if ip not in network:
                            raise ValidationError(
                                {"ip_address": "IP address is not within the configuration's IP range."}
                            )
                    except ValueError as e:
                        raise ValidationError({"configuration": f"Invalid IP range: {e}"})
