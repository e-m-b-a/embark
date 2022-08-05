from datetime import timedelta
import logging
import os
from random import choices
import shutil
import uuid
import re

from django.conf import settings
from django.db import models
from django import forms
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils.datetime_safe import datetime

# from hashid_field import HashidAutoField

from users.models import User as Userclass


logger = logging.getLogger(__name__)


class BooleanFieldExpertModeForm(forms.BooleanField):
    """
    class BooleanFieldExpertModeForm
    Extension of forms.BooleanField to support expert_mode and readonly option for BooleanFields in Forms
    """
    def __init__(self, *args, **kwargs):
        self.expert_mode = kwargs.pop('expert_mode', True)
        self.readonly = kwargs.pop('readonly', False)
        # super(BooleanFieldExpertModeForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)


class BooleanFieldExpertMode(models.BooleanField):
    """
    class BooleanFieldExpertModeForm
    Extension of models.BooleanField to support expert_mode and readonly for BooleanFields option for Models
    """
    def __init__(self, *args, **kwargs):
        self.expert_mode = kwargs.pop('expert_mode', True)
        self.readonly = kwargs.pop('readonly', False)
        # super(BooleanFieldExpertMode, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class': BooleanFieldExpertModeForm, 'expert_mode': self.expert_mode, 'readonly': self.readonly}
        defaults.update(kwargs)
        return models.Field.formfield(self, **defaults)


class CharFieldExpertModeForm(forms.CharField):
    """
    class BooleanFieldExpertModeForm
    Extension of forms.CharField to support expert_mode and readonly for CharField option for Forms
    """
    def __init__(self, *args, **kwargs):
        self.expert_mode = kwargs.pop('expert_mode', True)
        self.readonly = kwargs.pop('readonly', False)
        # super(CharFieldExpertModeForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)


class TypedChoiceFieldExpertModeForm(forms.TypedChoiceField):
    """
    class BooleanFieldExpertModeForm
    Extension of forms.TypedChoiceField to support expert_mode and readonly for TypedChoiceField option for Forms
    """
    def __init__(self, *args, **kwargs):
        self.expert_mode = kwargs.pop('expert_mode', True)
        self.readonly = kwargs.pop('readonly', False)
        # super(TypedChoiceFieldExpertModeForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)


class CharFieldExpertMode(models.CharField):
    """
    class CharFieldExpertMode
    Extension of models.BooleanField to support expert_mode and readonly for CharField option for Models
    """
    def __init__(self, *args, **kwargs):
        self.expert_mode = kwargs.pop('expert_mode', True)
        self.readonly = kwargs.pop('readonly', False)
        # super(CharFieldExpertMode, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class': CharFieldExpertModeForm, 'choices_form_class': TypedChoiceFieldExpertModeForm, 'expert_mode': self.expert_mode, 'readonly': self.readonly}
        defaults.update(kwargs)
        return models.Field.formfield(self, **defaults)


class FirmwareFile(models.Model):
    """
    class FirmwareFile
    Model to store zipped or bin firmware file and upload date
    """
    MAX_LENGTH = 127

    # id = HashidAutoField(primary_key=True, prefix='fw_')
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=True)

    is_archive = models.BooleanField(default=False, blank=True)
    upload_date = models.DateTimeField(default=datetime.now, blank=True)
    user = models.ForeignKey(Userclass, on_delete=models.SET_NULL, related_name='Fw_Upload_User', null=True, blank=True)

    def get_storage_path(self, filename):
        # file will be uploaded to MEDIA_ROOT/<id>/<filename>
        return os.path.join(f"{self.pk}", filename)

    file = models.FileField(upload_to=get_storage_path)

    def get_abs_path(self):
        return f"{settings.MEDIA_ROOT}/{self.pk}/{self.file.name}"

    def get_abs_folder_path(self):
        return f"{settings.MEDIA_ROOT}/{self.pk}"

    # def __init__(self, *args, **kwargs):
    #    super().__init__(*args, **kwargs)
        # self.file_name = self.file.name

    def __str__(self):
        return f"{self.file.name.replace('/', ' - ')}"  # this the only sanitizing we do?


@receiver(pre_delete, sender=FirmwareFile)
def delete_fw_pre_delete_post(sender, instance, **kwargs):
    """
    callback function
    delete the firmwarefile and folder structure in storage on recieve
    """
    if sender.file:
        shutil.rmtree(instance.get_abs_folder_path(), ignore_errors=False, onerror=logger.error("Error when trying to delete %s", instance.get_abs_folder_path()))
    else:
        logger.error("No related FW found for delete request: %s", str(sender))


class FirmwareAnalysis(models.Model):
    """
    class Firmware
    Model of firmware to be analyzed, basic/expert emba flags and metadata on the analyze process
    (1 FirmwareFile --> n FirmwareAnalysis)
    """
    MAX_LENGTH = 127

    # pk
    # id = HashidAutoField(primary_key=True, prefix='fwA_')
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=True)
    # user
    user = models.ForeignKey(Userclass, on_delete=models.SET_NULL, related_name='Fw_Analysis_User', null=True)
    # pid from within boundedexec
    pid = models.BigIntegerField(help_text='process id of subproc', verbose_name='PID', blank=True, null=True)

    firmware = models.ForeignKey(FirmwareFile, on_delete=models.SET_NULL, help_text='', null=True, editable=True)
    firmware_name = models.CharField(editable=True, default="File unknown", max_length=MAX_LENGTH)

    # emba basic flags
    version = CharFieldExpertMode(
        help_text='Firmware version', verbose_name="Firmware version", max_length=MAX_LENGTH,
        blank=True, expert_mode=False)
    vendor = CharFieldExpertMode(
        help_text='Firmware vendor', verbose_name="Firmware vendor", max_length=MAX_LENGTH,
        blank=True, expert_mode=False)
    device = CharFieldExpertMode(
        help_text='Device', verbose_name="Device", max_length=MAX_LENGTH, blank=True,
        expert_mode=False)
    notes = CharFieldExpertMode(
        help_text='Testing notes', verbose_name="Testing notes", max_length=MAX_LENGTH,
        blank=True, expert_mode=False)

    # emba expert flags
    firmware_Architecture = CharFieldExpertMode(
        choices=[(None, 'Select architecture'), ('MIPS', 'MIPS'), ('ARM', 'ARM'), ('x86', 'x86'), ('x64', 'x64'), ('PPC', 'PPC')],
        verbose_name="Select architecture of the linux firmware",
        help_text='Architecture of the linux firmware [MIPS, ARM, x86, x64, PPC] -a will be added',
        max_length=MAX_LENGTH, blank=True, expert_mode=True)
    user_emulation_test = BooleanFieldExpertMode(help_text='Enables automated qemu emulation tests', default=False, expert_mode=True, blank=True)
    system_emulation_test = BooleanFieldExpertMode(help_text='Enables automated qemu system emulation tests', default=False, expert_mode=True, blank=True)
    deep_extraction = BooleanFieldExpertMode(help_text='Enable deep extraction - try to extract every file two times with binwalk (WARNING: Uses a lot of disk space)'
        , default=False, expert_mode=True, blank=True)
    cwe_checker = BooleanFieldExpertMode(help_text='Enables cwe-checker,-c will be added', default=False, expert_mode=True, blank=True)
    online_checks = BooleanFieldExpertMode(help_text='Activate online checks (e.g. upload and test with VirusTotal)', default=False, expert_mode=True, blank=True)

    # TODO add -C and -k option

    # removed
    """
    dev_mode = BooleanFieldExpertMode(
        help_text='Run emba in developer mode, -D will be added ', default=False, expert_mode=True, blank=True)
    log_path = BooleanFieldExpertMode(
        help_text='Ignores log path check, -i will be added', default=False, expert_mode=True, blank=True)
    grep_able_log = BooleanFieldExpertMode(
        help_text='Create grep-able log file in [log_path]/fw_grep.log, -g will be added', default=True,
        expert_mode=True, blank=True)
    relative_paths = BooleanFieldExpertMode(
        help_text='Prints only relative paths, -s will be added', default=True, expert_mode=True, blank=True)
    ANSI_color = BooleanFieldExpertMode(
        help_text='Adds ANSI color codes to log, -z will be added', default=True, expert_mode=True, blank=True)
    web_reporter = BooleanFieldExpertMode(
        help_text='Activates web report creation in log path, -W will be added', default=True, expert_mode=True,
        blank=True)
    dependency_check = BooleanFieldExpertMode(
        help_text=' Checks dependencies but ignore errors, -F will be added', default=True, expert_mode=True,
        blank=True)
    multi_threaded = BooleanFieldExpertMode(
        help_text='Activate multi threading (destroys regular console output), -t will be added', default=True,
        expert_mode=True, blank=True)
    firmware_remove = BooleanFieldExpertMode(
        help_text='Remove extracted firmware file/directory after testint, -r will be added', default=True,
        expert_mode=True, blank=True)
    """

    # embark meta data
    path_to_logs = models.FilePathField(default="/", blank=True)
    start_date = models.DateTimeField(default=datetime.now, blank=True)
    end_date = models.DateTimeField(default=datetime.min, blank=True)
    scan_time = models.DurationField(default=timedelta(), blank=True)
    duration = models.CharField(blank=True, null=True, max_length=100, help_text='')
    finished = models.BooleanField(default=False, blank=False)
    failed = models.BooleanField(default=True, blank=False)

    class Meta:
        app_label = 'uploader'

        """
        build shell command from input fields
        :params: None
        :return:
        """

    # def __init__(self, *args, **kwargs):
    #    super().__init__(*args, **kwargs)
    #    self.firmware_name = self.firmware.file.name

    def __str__(self):
        return f"{self.id}({self.firmware})"

    def get_flags(self):    # FIXME 
        """
        build shell command from input fields

        :return: string formatted input flags for emba
        """
        command = ""
        if self.version:
            command = command + " -X " + re.sub("[^A-Za-z0–9\.\-\_]+", "", str(self.version))
        if self.vendor:
            command = command + " -Y " + re.sub("[^A-Za-z0–9\-\_]+", "", str(self.vendor))
        if self.device:
            command = command + " -Z " + re.sub("[^A-Za-z0–9\-\_]+", "", str(self.device))
        if self.notes:
            command = command + " -N " + re.sub("[^A-Za-z0–9\-\_]+", "", str(self.notes))
        if self.firmware_Architecture:
            command = command + " -a " + str(self.firmware_Architecture)
        if self.cwe_checker:
            command = command + " -c"
        if self.deep_extraction:
            command = command + " -x"
        if self.user_emulation_test:
            command = command + " -E"
        if self.system_emulation_test:
            command = command + " -Q"
        # running emba
        logger.info("final emba parameters %s", command)
        return command


class ResourceTimestamp(models.Model):
    """
    class ResourceTimestamp
    Model to store zipped or bin firmware file and upload date
    """

    timestamp = models.DateTimeField(default=datetime.now)
    cpu_percentage = models.FloatField(default=0.0)
    memory_percentage = models.FloatField(default=0.0)
