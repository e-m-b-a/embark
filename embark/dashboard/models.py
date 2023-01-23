from django.db import models
from django.core.validators import MinLengthValidator

from uploader.models import FirmwareAnalysis


class Vulnerability(models.Model):
    """
    Many-to-Many object for CVEs
    """
    cve = models.CharField(max_length=15, validators=[MinLengthValidator(15)], help_text='CVE-XXXX-XXXXXX')
    info = models.JSONField(null=True)


class Result(models.Model):
    """
    1-to-1 Result object for related FirmwareAnalysis
    """
    # meta
    firmware_analysis = models.OneToOneField(FirmwareAnalysis, on_delete=models.CASCADE, primary_key=True)
    emba_command = models.CharField(blank=True, null=True, max_length=(FirmwareAnalysis.MAX_LENGTH * 6), help_text='')
    restricted = models.BooleanField(default=False, help_text='')

    # base identifier
    os_verified = models.CharField(blank=True, null=True, max_length=256, help_text='')
    architecture_verified = models.CharField(blank=True, null=True, max_length=100, help_text='')
    architecture_unverified = models.CharField(blank=True, null=True, max_length=100, help_text='')
    files = models.IntegerField(default=0, help_text='')
    directories = models.IntegerField(default=0, help_text='')
    entropy_value = models.FloatField(default=0.0, help_text='')

    # f50
    cve_high = models.IntegerField(default=0, help_text='')
    cve_medium = models.IntegerField(default=0, help_text='')
    cve_low = models.IntegerField(default=0, help_text='')
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

    vulnerability = models.ManyToManyField(Vulnerability, help_text='CVE/Vulnerability', related_query_name='CVE', editable=True, blank=True)
