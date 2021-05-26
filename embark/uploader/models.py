from django.conf import settings
from django.db import models
from django import forms
from django.utils.datetime_safe import datetime


class BooleanFieldExpertModeForm(forms.BooleanField):
    def __init__(self, input_formats=None, *args, **kwargs):
        self.expert_mode = kwargs.pop('expert_mode', True)
        super(BooleanFieldExpertModeForm, self).__init__(*args, **kwargs)


class BooleanFieldExpertMode(models.BooleanField):
    def __init__(self, *args, **kwargs):
        self.expert_mode = kwargs.pop('expert_mode', True)
        super(BooleanFieldExpertMode, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class': BooleanFieldExpertModeForm, 'expert_mode': self.expert_mode}
        defaults.update(kwargs)
        return models.Field.formfield(self, **defaults)


class CharFieldExpertModeForm(forms.CharField):
    def __init__(self, input_formats=None, *args, **kwargs):
        self.expert_mode = kwargs.pop('expert_mode', True)
        super(CharFieldExpertModeForm, self).__init__(*args, **kwargs)


class CharFieldExpertMode(models.CharField):
    def __init__(self, *args, **kwargs):
        self.expert_mode = kwargs.pop('expert_mode', True)
        super(CharFieldExpertMode, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class': CharFieldExpertModeForm, 'expert_mode': self.expert_mode}
        defaults.update(kwargs)
        return models.Field.formfield(self, **defaults)


class FirmwareFile(models.Model):

    def get_storage_path(self, filename):
        # file will be uploaded to MEDIA_ROOT/<filename>
        return f"{filename}"

    MAX_LENGTH = 127

    file = models.FileField(upload_to=get_storage_path)
    upload_date = models.DateTimeField(default=datetime.now, blank=True)

    def get_abs_path(self):
        return f"/app/embark/{settings.MEDIA_ROOT}/{self.file.name}"


class Firmware(models.Model):

    MAX_LENGTH = 127

    firmware = CharFieldExpertMode(help_text='', blank=False, max_length=MAX_LENGTH)

    version = CharFieldExpertMode(
        help_text='Firmware version (double quote your input)', verbose_name=u"Firmware version", max_length=MAX_LENGTH,
        blank=True, expert_mode=False)
    vendor = CharFieldExpertMode(
        help_text='Firmware vendor (double quote your input)', verbose_name=u"Firmware vendor", max_length=MAX_LENGTH,
        blank=True, expert_mode=False)
    device = CharFieldExpertMode(
        help_text='Device (double quote your input)', verbose_name=u"Device", max_length=MAX_LENGTH, blank=True,
        expert_mode=False,)
    notes = CharFieldExpertMode(
        help_text='Testing notes (double quote your input)', verbose_name=u"Testing notes", max_length=MAX_LENGTH,
        blank=True, expert_mode=False)

    firmware_Architecture = CharFieldExpertMode(
        choices=[('MIPS', 'MIPS'), ('ARM', 'ARM'), ('x86', 'x86'), ('x64', 'x64'), ('PPC', 'PPC')],
        verbose_name=u"Select architecture of the linux firmware",
        help_text='Architecture of the linux firmware [MIPS, ARM, x86, x64, PPC] -a will be added',
        max_length=MAX_LENGTH, blank=True, expert_mode=False)

    cwe_checker = BooleanFieldExpertMode(
        help_text='Enables cwe-checker,-c will be added', default=False, expert_mode=True, blank=True)
    docker_container = BooleanFieldExpertMode(
        help_text='Run emba in docker container, -D will be added', default=False, expert_mode=True, blank=True)
    deep_extraction = BooleanFieldExpertMode(
        help_text='Enable deep extraction, -x will be added', default=False, expert_mode=True, blank=True)
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
    emulation_test = BooleanFieldExpertMode(
        help_text='Enables automated qemu emulation tests, -E will be added', default=False, expert_mode=True,
        blank=True)
    dependency_check = BooleanFieldExpertMode(
        help_text=' Checks dependencies but ignore errors, -F will be added', default=True, expert_mode=True,
        blank=True)
    multi_threaded = BooleanFieldExpertMode(
        help_text='Activate multi threading (destroys regular console output), -t will be added', default=True,
        expert_mode=True, blank=True)

    class Meta:
        app_label = 'uploader'

    """
        build shell command from input fields

        :params: None

        :return:
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_flags(self):
        command = ""
        if self.version:
            command = command + " -X " + str(self.version)
        if self.vendor:
            command = command + " -Y " + str(self.vendor)
        if self.device:
            command = command + " -Z " + str(self.device)
        if self.notes:
            command = command + " -N " + str(self.notes)
        if self.firmware_Architecture:
            command = command + " -a " + str(self.firmware_Architecture)
        if self.cwe_checker:
            command = command + " -c"
        if self.docker_container:
            command = command + " -D"
        if self.deep_extraction:
            command = command + " -x"
        if self.log_path:
            command = command + " -i"
        if self.grep_able_log:
            command = command + " -g"
        if self.relative_paths:
            command = command + " -s"
        if self.ANSI_color:
            command = command + " -z"
        if self.web_reporter:
            command = command + " -W"
        if self.emulation_test:
            command = command + " -E"
        if self.dependency_check:
            command = command + " -F"
        if self.multi_threaded:
            command = command + " -t"
        # running emba
        return command
