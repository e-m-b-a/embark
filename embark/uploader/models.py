from datetime import timedelta
import logging
import os
import shutil
import uuid
import re

from django.conf import settings
from django.db import models
from django import forms
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils.datetime_safe import datetime
from porter.models import LogZipFile

# from hashid_field import HashidAutoField

from users.models import User as Userclass


logger = logging.getLogger(__name__)


def jsonfield_default_value():
    """
    keys: percentage, analysis, firmwarename, last_update, last_module, module_list, last_phase, phase_list
    """
    return {
        "percentage": 0,
        'analysis': "",
        'firmware_name': "",
        'last_update': "",
        'last_module': "",
        'module_list': [],
        'last_phase': "",
        'phase_list': [],
        'finished': False
    }


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
    class TypedChoiceFieldExpertModeForm
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


class MultipleChoiceFieldExpertMode(forms.TypedMultipleChoiceField):
    """
    class TypedMultipleChoiceFieldExpertMode
    extends for expertmode usage
    """
    def __init__(self, *args, **kwargs):
        self.expert_mode = kwargs.pop('expert_mode', True)
        self.readonly = kwargs.pop('readonly', False)
        super().__init__(*args, **kwargs)


class MultipleCharFieldExpertMode(models.CharField):
    """
    class MultipleCharFieldExpertMode
    Extension of models.BooleanField to support expert_mode and readonly for CharField option for Models
    """
    def __init__(self, *args, **kwargs):
        self.expert_mode = kwargs.pop('expert_mode', True)
        self.readonly = kwargs.pop('readonly', False)
        # super(CharFieldExpertMode, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class': CharFieldExpertModeForm, 'choices_form_class': MultipleChoiceFieldExpertMode, 'expert_mode': self.expert_mode, 'readonly': self.readonly}
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


class Vendor (models.Model):
    """
    class Vendor
    Model of vendor for devices
    (1 vendor --> n devices)
    """
    MAX_LENGTH = 127

    vendor_name = models.CharField(
        help_text='Vendor name', verbose_name="vendor name", max_length=MAX_LENGTH,
        blank=True, unique=True)

    class Meta:
        ordering = ['vendor_name']

    def __str__(self):
        return self.vendor_name


class Label (models.Model):
    """
    class Label
    Model for labels
    ( 1 device --> n labels )
    """
    MAX_LENGTH = 127

    label_name = models.CharField(
        help_text='label name', verbose_name="label name", max_length=MAX_LENGTH,
        blank=True, unique=True)
    label_date = models.DateTimeField(default=datetime.now, blank=True)

    class Meta:
        ordering = ['label_name']

    def __str__(self):
        return self.label_name


class Device(models.Model):
    """
    class Device
    Model of the device under test
    (m Devices <---> n FirmwareFiles)
    (m Device <----> p Analyses )
    * assumes device revisions as different devices etc.
    * case sensitive
    """
    MAX_LENGTH = 127

    device_name = models.CharField(help_text='Device name', verbose_name="Device name", max_length=MAX_LENGTH, blank=True)
    device_vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True)
    device_label = models.ForeignKey(Label, on_delete=models.SET_NULL, null=True, help_text='label/tag', related_query_name='label', editable=True, blank=True)   # TODO make many to many field
    device_date = models.DateTimeField(default=datetime.now, blank=True)
    device_user = models.ForeignKey(Userclass, on_delete=models.SET_NULL, related_name='Device_User', null=True)    # TODO change acces control to usergroup??

    visible = models.BooleanField(editable=True, default=True)

    class Meta:
        ordering = ['device_name']
        unique_together = ['device_name', 'device_vendor']

    def __str__(self):
        return f"{self.device_name}({self.device_vendor})"


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
    notes = CharFieldExpertMode(
        help_text='Testing notes', verbose_name="Testing notes", max_length=MAX_LENGTH,
        blank=True, expert_mode=False)

    # new hardware oriented tracking
    device = models.ManyToManyField(Device, help_text='device/platform', related_query_name='device', editable=True, max_length=MAX_LENGTH, blank=True)

    # emba expert flags
    firmware_Architecture = CharFieldExpertMode(
        choices=[
            (None, 'Select architecture'), ('MIPS', 'MIPS'), ('MIPS64R2', 'MIPS64R2'), ('MIPS64_III', 'MIPS64_III'), ('MIPS64_N32', 'MIPS64_N32'),
            ('ARM', 'ARM'), ('ARM64', 'ARM64'),
            ('x86', 'x86'), ('x64', 'x64'),
            ('PPC', 'PPC'), ('PPC64', 'PPC64'),
            ('NIOS2', 'NIOS2'), ('RISCV', 'RISCV'), ('QCOM_DSP6', 'QCOM_DSP6')
        ],
        verbose_name="Select architecture of the linux firmware",
        help_text='Architecture of the linux firmware [MIPS, ARM, x86, x64, PPC, NIOS2] -a will be added (note: other options are not in use yet)',
        max_length=MAX_LENGTH, blank=True, expert_mode=True
    )

    # expertmode options
    user_emulation_test = BooleanFieldExpertMode(help_text='Enables automated qemu emulation tests', default=False, expert_mode=True, blank=True)
    system_emulation_test = BooleanFieldExpertMode(help_text='Enables automated qemu system emulation tests', default=False, expert_mode=True, blank=True)

    # S-modules
    scan_modules = MultipleCharFieldExpertMode(
        choices=[
            ('s02', 'S02_UEFI_FwHunt'),
            ('s03', 'S03_firmware_bin_base_analyzer'),
            ('s05', 'S05_firmware_details'),
            ('s06', 'S06_distribution_identification'),
            ('s08', 'S08_package_mgmt_extractor'),
            ('s09', 'S09_firmware_base_version_check'),
            ('s10', 'S10_binaries_basic_check'),
            ('s12', 'S12_binary_protection'),
            ('s13', 'S13_weak_func_check'),
            ('s14', 'S14_weak_func_radare_check'),
            ('s15', 'S15_bootloader_check'),
            ('s20', 'S20_shell_check'),
            ('s21', 'S21_python_check'),
            ('s22', 'S22_php_check'),
            ('s24', 'S24_kernel_bin_identifier'),
            ('s25', 'S25_kernel_check'),
            ('s35', 'S35_http_file_check'),
            ('s40', 'S40_weak_perm_check'),
            ('s45', 'S45_pass_file_check'),
            ('s50', 'S50_authentication_check'),
            ('s55', 'S55_history_file_check'),
            ('s60', 'S60_cert_file_check'),
            ('s65', 'S65_config_file_check'),
            ('s70', 'S70_hidden_file_check'),
            ('s75', 'S75_network_check'),
            ('s80', 'S80_cronjob_check'),
            ('s85', 'S85_ssh_check'),
            ('s90', 'S90_mail_check'),
            ('s95', 'S95_interesting_binaries_check'),
            ('s99', 'S99_grepit')
        ],
        help_text='Enable/disable specific scan-modules for your analysis',
        blank=True,
        expert_mode=True,
        max_length=150
    )

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
    # Zip file for porting and download
    zip_file = models.ForeignKey(LogZipFile, on_delete=models.SET_NULL, help_text='', null=True, editable=True)

    # embark meta data
    path_to_logs = models.FilePathField(default="/", blank=True)
    log_size = models.PositiveBigIntegerField(default=0, blank=True)
    start_date = models.DateTimeField(default=datetime.now, blank=True)
    end_date = models.DateTimeField(default=datetime.min, blank=True)
    scan_time = models.DurationField(default=timedelta(), blank=True)
    duration = models.CharField(blank=True, null=True, max_length=100, help_text='')
    finished = models.BooleanField(default=False, blank=False)
    failed = models.BooleanField(default=False, blank=False)

    # status/logreader-stuff
    status = models.JSONField(null=False, default=jsonfield_default_value)

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

    def get_flags(self):
        """
        build shell command from input fields

        :return: string formatted input flags for emba
        """

        command = ""
        if self.version:
            command = command + r" -X " + "\"" + re.sub(r"[^a-zA-Z0-9\.\-\_\ \+]+", "", str(self.version)) + "\""
        if self.device:
            devices = self.device.all()
            logger.debug("get_flags - device - to dict query returns %s", devices)
            _device_name_list = []
            _device_vendor_list = []
            for _device in devices:
                _device_name_list.append(_device.device_name)
                _device_vendor_list.append(_device.device_vendor.vendor_name)
            logger.debug("get_flags - device_name - to name dict %s", _device_name_list)
            logger.debug("get_flags - vendor_name - to name dict %s", _device_vendor_list)
            command = command + r" -Z " + "\"" + re.sub(r"[^a-zA-Z0-9\-\_\ ]+", "", str(_device_name_list)) + "\""
            command = command + r" -Y " + "\"" + re.sub(r"[^a-zA-Z0-9\-\_\ ]+", "", str(_device_vendor_list)) + "\""
        if self.notes:
            command = command + r" -N " + "\"" + re.sub(r"[^a-zA-Z0-9\.\-\_\ ]+", "", str(self.notes)) + f" (uuid:{self.id})" + "\""
        if self.firmware_Architecture:
            command = command + r" -a " + str(self.firmware_Architecture)
        if self.user_emulation_test:
            command = command + r" -E"
        if self.system_emulation_test:
            command = command + r" -Q"
        if self.scan_modules:
            for module_ in self.scan_modules:
                command = command + r" -m " + str(module_)
            # TODO add all p modules????

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
