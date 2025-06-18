import ipaddress

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from users.models import User
from workers.codeql_ignore import new_autoadd_client


class Configuration(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='configuration', help_text="User who created this configuration")
    name = models.CharField(max_length=150, blank=True, null=True, help_text="Name of the configuration")
    ssh_user = models.CharField(max_length=150, blank=True, null=True, help_text="SSH user of the worker nodes")
    ssh_password = models.CharField(max_length=150, blank=True, null=True, help_text="SSH password of the worker nodes")
    ip_range = models.TextField(blank=True, null=True, help_text="IP range of the worker nodes")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Date time when this entry was created")


class Worker(models.Model):
    class ConfigStatus(models.TextChoices):  # pylint: disable=too-many-ancestors
        UNCONFIGURED = "U", _("Unconfigured")
        CONFIGURING = "I", _("Configuring")
        CONFIGURED = "C", _("Configured")
        ERROR = "E", _("Error")

    class AnalysisStatus(models.TextChoices): # pylint: disable=too-many-ancestors
        RUNNING = "R", _("Running")
        UNASSIGNED = "U", _("Analysis unassigned")

    configurations = models.ManyToManyField(Configuration, related_name='workers', blank=True)
    name = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(unique=True)
    system_info = models.JSONField()
    reachable = models.BooleanField(default=False)
    status = models.CharField(max_length=1, choices=ConfigStatus, default=ConfigStatus.UNCONFIGURED)
    analysis_id = models.CharField(max_length=100, blank=True, null=True, help_text="ID of the analysis currently running on this worker")
    sync_enabled = models.BooleanField(default=False)

    def clean(self):
        super().clean()
        if self.configurations.exists():
            for config in self.configurations.all():
                if config.ip_range:
                    try:
                        network = ipaddress.ip_network(config.ip_range, strict=False)
                        ip_address = ipaddress.ip_address(self.ip_address)
                        if ip_address not in network:
                            raise ValidationError(
                                {"ip_address": "IP address is not within the configuration's IP range."}
                            )
                    except ValueError as value_error:
                        raise ValidationError({"configuration": f"Invalid IP range: {value_error}"}) from value_error

    def ssh_connect(self, configuration_id=None):
        ssh_client = new_autoadd_client()
        configuration = self.configurations.first() if configuration_id is None else self.configurations.get(id=configuration_id)

        ssh_client.connect(self.ip_address, username=configuration.ssh_user, password=configuration.ssh_password)

        # save the ssh user and password so they can later be used in commands
        ssh_client.ssh_user = configuration.ssh_user
        ssh_client.ssh_pw = configuration.ssh_password

        return ssh_client
