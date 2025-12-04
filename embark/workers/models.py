__copyright__ = 'Copyright 2025 The AMOS Projects'
__author__ = 'ashiven, ClProsser, SirGankalot'
__license__ = 'MIT'

import os
import ipaddress
from pathlib import Path
import socket
import paramiko

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from users.models import User
from workers.codeql_ignore import new_autoadd_client


class Configuration(models.Model):

    class ScanStatus(models.TextChoices):  # pylint: disable=too-many-ancestors
        NEW = "N", _("New")
        SCANNING = "S", _("Scanning")
        FINISHED = "F", _("Finished")
        ERROR = "E", _("Error")

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='configuration')
    name = models.CharField(max_length=150)
    ssh_user = models.CharField(max_length=150)
    ssh_password = models.CharField(max_length=150, help_text="Allowed special characters: @ # $ % ^ & + = ! ( ) { } [ ] _ - | \\")
    ssh_private_key = models.TextField()
    ssh_public_key = models.TextField()
    ip_range = models.CharField(max_length=20, help_text="CIDR notation (e.g., 192.168.1.0/24)")
    created_at = models.DateTimeField(auto_now_add=True)
    scan_status = models.CharField(max_length=1, choices=ScanStatus, default=ScanStatus.NEW)
    log_location = models.FilePathField(path=f"{settings.WORKER_LOG_ROOT_ABS}/{settings.WORKER_CONFIGURATION_LOGS}")

    def write_log(self, string):
        """
        Writes into self.log_location
        :returns: None
        """
        if not Path(self.log_location).is_file():
            with open(self.log_location, 'x') as log_file:
                log_file.write(string + "\n")
        else:
            with open(self.log_location, 'a') as log_file:
                log_file.write(string + "\n")

    def _ssh_key_paths(self):
        """
        Returns ssh key paths
        :return: private_key_path
        :return: public_key_path
        """
        private_key_path = f"{settings.WORKER_KEY_LOCATION}/key_{self.id}"
        public_key_path = f"{settings.WORKER_KEY_LOCATION}/key_{self.id}.pub"

        return private_key_path, public_key_path

    def ensure_ssh_keys(self):
        """
        Ensures that SSH keys are created on disk
        :return: private_key_path
        :return: public_key_path
        """
        os.makedirs(settings.WORKER_KEY_LOCATION, exist_ok=True)

        private_key_path, public_key_path = self._ssh_key_paths()

        if not os.path.isfile(private_key_path):
            with open(private_key_path, "a", encoding="utf-8") as file:
                file.write(self.ssh_private_key)

        if not os.path.isfile(public_key_path):
            with open(public_key_path, "a", encoding="utf-8") as file:
                file.write(self.ssh_public_key)

        return private_key_path, public_key_path

    def delete_ssh_keys(self):
        """
        Removes SSH keys from disk, if exists
        """
        private_key_path, public_key_path = self._ssh_key_paths()

        if os.path.isfile(private_key_path):
            os.remove(private_key_path)

        if os.path.isfile(public_key_path):
            os.remove(public_key_path)


def default_deb_list():
    return {}


class WorkerDependencyVersion(models.Model):
    emba = models.CharField(max_length=100, null=True)
    emba_head = models.CharField(max_length=40, null=True)
    nvd_head = models.CharField(max_length=40, null=True)
    nvd_time = models.DateTimeField(null=True)
    epss_head = models.CharField(max_length=40, null=True)
    epss_time = models.DateTimeField(null=True)
    deb_list = models.JSONField(default=default_deb_list)
    deb_list_diff = models.JSONField(default=default_deb_list)

    emba_outdated = models.BooleanField(default=True)
    external_outdated = models.BooleanField(default=True)
    deb_outdated = models.BooleanField(default=True)

    def get_external_version(self):
        return f"{self.nvd_head},{self.epss_head}"

    def is_external_outdated(self, version: str):
        nvd_head, epss_head = version.split(',')

        return nvd_head != self.nvd_head or epss_head != self.epss_head


class Worker(models.Model):

    class ConfigStatus(models.TextChoices):  # pylint: disable=too-many-ancestors
        UNCONFIGURED = "U", _("Unconfigured")
        CONFIGURING = "I", _("Configuring")
        CONFIGURED = "C", _("Configured")
        ERROR = "E", _("Error")

    configurations = models.ManyToManyField(Configuration, related_name='workers', blank=True)
    name = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(unique=True)
    system_info = models.JSONField(default=dict, blank=True, null=True)
    reachable = models.BooleanField(default=False)
    status = models.CharField(max_length=1, choices=ConfigStatus, default=ConfigStatus.UNCONFIGURED)
    analysis_id = models.UUIDField(blank=True, null=True, help_text="ID of the analysis currently running on this worker")
    last_reached = models.DateTimeField(auto_now_add=True)
    log_location = models.FilePathField(path=f"{settings.WORKER_LOG_ROOT_ABS}/{settings.WORKER_WORKER_LOGS}")

    dependency_version = models.OneToOneField(
        WorkerDependencyVersion,
        on_delete=models.CASCADE,
        null=True
    )

    def write_log(self, string):
        """
        Writes into self.log_location
        :returns: None
        """
        if not Path(self.log_location).is_file():
            with open(self.log_location, 'x') as log_file:
                log_file.write(string)
        else:
            with open(self.log_location, 'a') as log_file:
                log_file.write(string)

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

    def ssh_connect(self, use_password=False, timeout=30):
        """
        Tries to establish an ssh connection with each configuration and returns the first successful connection
        :param use_password: Use SSH password instead of SSH key
        :param timeout: max ssh connect timeout
        """
        ssh_client = new_autoadd_client()

        for configuration in self.configurations.all():
            try:
                if use_password:
                    ssh_client.connect(self.ip_address, username=configuration.ssh_user, password=configuration.ssh_password, timeout=timeout)
                else:
                    private_key_path, _ = configuration.ensure_ssh_keys()
                    pkey = paramiko.RSAKey.from_private_key_file(private_key_path)
                    ssh_client.connect(self.ip_address, username=configuration.ssh_user, pkey=pkey, look_for_keys=False, allow_agent=False, timeout=timeout)

                # save the ssh user so it can later be used in commands
                ssh_client.ssh_user = configuration.ssh_user
                break
            except (paramiko.SSHException, socket.error):
                continue

        if ssh_client.get_transport() is None or not ssh_client.get_transport().is_active():
            raise paramiko.SSHException("Failed to connect to worker with any configuration.")
        self.write_log(f"SSH Connection to {self.ip_address} established")
        return ssh_client


class DependencyType(models.TextChoices):  # pylint: disable=too-many-ancestors
    DEPS = "D", _("APT Dependencies")
    REPO = "R", _("GH Repository")
    EXTERNAL = "E", _("EXTERNAL DIR")
    DOCKERIMAGE = "DO", _("DOCKER IMAGE")


class WorkerUpdate(models.Model):

    dependency_type = models.CharField(max_length=2, choices=DependencyType)
    version = models.CharField(max_length=100, default="latest")
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_type(self):
        return DependencyType(self.dependency_type)


class DependencyVersion(models.Model):
    """
    Available dependency version according to update check.
    This version is not necesserily cached
    """
    emba = models.CharField(max_length=100, default="latest")
    emba_head = models.CharField(max_length=40, default="latest")
    nvd_head = models.CharField(max_length=40, default="latest")
    nvd_time = models.DateTimeField(null=True)
    epss_head = models.CharField(max_length=40, default="latest")
    epss_time = models.DateTimeField(null=True)
    deb_list = models.JSONField(default=default_deb_list)

    def get_external_version(self):
        return f"{self.nvd_head},{self.epss_head}"


class CachedDependencyVersion(models.Model):
    """
    Cached dependency versions available for download on worker nodes
    """
    emba = models.CharField(max_length=100, default="latest")
    emba_history = models.JSONField(default=list)
    emba_head = models.CharField(max_length=40, default="latest")
    emba_head_history = models.JSONField(default=list)
    nvd_head = models.CharField(max_length=40, default="latest")
    nvd_head_history = models.JSONField(default=list)
    epss_head = models.CharField(max_length=40, default="latest")
    epss_head_history = models.JSONField(default=list)

    def get_external_version(self):
        return f"{self.nvd_head},{self.epss_head}"

    def set_emba(self, version: str):
        self.emba = version
        history = list(self.emba_history)

        if version != "latest":
            # "latest" is never old
            history.append(version)

        self.emba_history = history

    def set_emba_head(self, version: str):
        self.emba_head = version
        history = list(self.emba_head_history)

        if version != "latest":
            # "latest" is never old
            history.append(version)

        self.emba_head_history = history

    def set_external_version(self, version: str):
        nvd_head, epss_head = version.split(',')

        self.nvd_head = nvd_head
        history = list(self.nvd_head_history)

        if nvd_head != "latest":
            # "latest" is never old
            history.append(nvd_head)

        self.nvd_head_history = history

        self.epss_head = epss_head
        history = list(self.epss_head_history)

        if epss_head != "latest":
            # "latest" is never old
            history.append(epss_head)

        self.epss_head_history = history

    def external_already_installed(self, version: str):
        """
        Checks if external version was already installed
        :param version: the version string containing nvd and epss version
        :returns: True if both were already installed, otherwise false
        """
        nvd_head, epss_head = version.split(',')

        return nvd_head in self.nvd_head_history and epss_head in self.epss_head_history


class OrchestratorState(models.Model):
    free_workers = models.ManyToManyField(Worker, related_name='free_workers', help_text="Workers that are currently free")
    busy_workers = models.ManyToManyField(Worker, related_name='busy_workers', help_text="Workers that are currently busy")
    tasks = models.JSONField(default=list, null=True, help_text="List of tasks to be processed by workers")


class DependencyState(models.Model):
    class AvailabilityType(models.TextChoices):  # pylint: disable=too-many-ancestors
        UNAVAILABLE = "U", _("Unavailable")
        IN_PROGRESS = "I", _("In progress")
        AVAILABLE = "A", _("Available")

    used_by = models.ManyToManyField(Worker, related_name='used_by', help_text="Workers that are currently using the dependency")
    dependency_type = models.CharField(max_length=2, choices=DependencyType)
    availability = models.CharField(max_length=1, choices=AvailabilityType, default=AvailabilityType.UNAVAILABLE)
