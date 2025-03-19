__copyright__ = 'Copyright 2022-2025 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

import os
import uuid
from django.conf import settings
from django.db import models
from django.core.validators import MinLengthValidator
from django.utils import timezone

from uploader.models import FirmwareAnalysis


class Vulnerability(models.Model):
    """
    Many-to-Many object for CVEs
    """
    cve = models.CharField(max_length=18, validators=[MinLengthValidator(13)], help_text='CVE-XXXX-XXXXXXX')
    info = models.JSONField(null=True, editable=True)


class SoftwareInfo(models.Model):
    """
    Many-to-one object for SBOM entries
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=True)
    type = models.CharField(verbose_name="type of blob", blank=False, editable=True, default="NA", max_length=256)
    name = models.CharField(verbose_name="software name", blank=False, editable=True, default="NA", max_length=256)
    group = models.CharField(verbose_name="grouping", blank=False, editable=True, default="NA", max_length=256)
    version = models.CharField(verbose_name="software version", blank=False, editable=True, default="1.0", max_length=32)
    supplier = models.CharField(verbose_name="software supplier", blank=False, editable=True, default="NA", max_length=1024)
    license = models.CharField(verbose_name="software license", blank=False, editable=True, default="NA", max_length=1024)
    hashes = models.CharField(verbose_name="identivication hash", blank=False, editable=True, default="NA", max_length=1024)
    cpe = models.CharField(verbose_name="CPE identifier", blank=False, editable=True, default="NA", max_length=256)
    type = models.CharField(verbose_name="software type", blank=False, editable=True, default="data", max_length=50)
    purl = models.CharField(verbose_name="PUrl identifier", blank=False, editable=True, default="NA", max_length=256)
    description = models.CharField(verbose_name="description", blank=False, editable=True, default="NA", max_length=1024)
    properties = models.JSONField(verbose_name="Properties", null=True, editable=True, serialize=True)


class SoftwareBillOfMaterial(models.Model):
    """
    1-to-1 object for result
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=True)
    meta = models.CharField(verbose_name="meta data sbom", blank=False, editable=True, default="NA", max_length=1024)
    component = models.ManyToManyField(SoftwareInfo, help_text='Software Bill of Material', related_query_name='sbom', editable=True, blank=True)
    file = models.FilePathField(verbose_name='sbom_file', editable=True, default=os.path.join(settings.EMBA_LOG_ROOT, 'empty.json'), max_length=110)


class Result(models.Model):
    """
    1-to-1 Result object for related FirmwareAnalysis
    """
    # meta
    firmware_analysis = models.OneToOneField(FirmwareAnalysis, on_delete=models.CASCADE, primary_key=True)
    emba_command = models.CharField(blank=True, null=True, max_length=(FirmwareAnalysis.MAX_LENGTH * 6), help_text='')
    restricted = models.BooleanField(default=False, help_text='')
    date = models.DateTimeField(default=timezone.now, blank=True)

    # base identifier
    os_verified = models.CharField(blank=True, null=True, max_length=256, help_text='')
    architecture_verified = models.CharField(blank=True, null=True, max_length=100, help_text='')
    architecture_unverified = models.CharField(blank=True, null=True, max_length=100, help_text='')
    files = models.IntegerField(default=0, help_text='')
    directories = models.IntegerField(default=0, help_text='')
    entropy_value = models.FloatField(default=0.0, help_text='')

    # f50
    cve_critical = models.TextField(default='{}')
    cve_high = models.TextField(default='{}')
    cve_medium = models.TextField(default='{}')
    cve_low = models.TextField(default='{}')
    exploits = models.IntegerField(default=0, help_text='')
    metasploit_modules = models.IntegerField(default=0, help_text='')

    # s12
    canary = models.IntegerField(default=0, help_text='')
    canary_per = models.IntegerField(default=0, help_text='')
    relro = models.IntegerField(default=0, help_text='')
    relro_per = models.IntegerField(default=0, help_text='')
    no_exec = models.IntegerField(default=0, help_text='')
    no_exec_per = models.IntegerField(default=0, help_text='')
    pie = models.IntegerField(default=0, help_text='')
    pie_per = models.IntegerField(default=0, help_text='')
    stripped = models.IntegerField(default=0, help_text='')
    stripped_per = models.IntegerField(default=0, help_text='')

    # idk where to get
    certificates = models.IntegerField(default=0, help_text='')
    certificates_outdated = models.IntegerField(default=0, help_text='')
    shell_scripts = models.IntegerField(default=0, help_text='')
    shell_script_vulns = models.IntegerField(default=0, help_text='')
    yara_rules_match = models.IntegerField(default=0, help_text='')
    kernel_modules = models.IntegerField(default=0, help_text='')
    kernel_modules_lic = models.IntegerField(default=0, help_text='')
    interesting_files = models.IntegerField(default=0, help_text='')
    post_files = models.IntegerField(default=0, help_text='')

    strcpy = models.IntegerField(default=0, help_text='')
    versions_identified = models.IntegerField(default=0, help_text='')

    bins_checked = models.IntegerField(default=0, help_text='')
    strcpy_bin = models.TextField(default='{}')
    system_bin = models.TextField(default='{}')

    vulnerability = models.ManyToManyField(Vulnerability, help_text='CVE/Vulnerability', related_query_name='CVE', editable=True, blank=True)
    sbom = models.OneToOneField(SoftwareBillOfMaterial, help_text='Software Bill of Material', related_query_name='sbom', editable=True, blank=True, on_delete=models.CASCADE, null=True)
