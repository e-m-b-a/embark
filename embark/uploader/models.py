from django.db import models
from mongoengine import Document


class Firmware(models.Model):
    title = models.TextField(help_text='', blank=True)
    posted = models.DateTimeField(help_text='', auto_now_add=True, blank=True)
    url = models.TextField(help_text='', blank=True)
    version = models.TextField(help_text='Firmware version (double quote your input)')
    vendor = models.TextField(help_text='Firmware vendor (double quote your input)')
    device = models.TextField(help_text='Device (double quote your input)')
    notes = models.TextField(help_text='Testing notes (double quote your input)')
    firmware_Architecture = models.TextField(
        help_text='Architecture of the linux firmware [MIPS, ARM, x86, x64, PPC], -a will be added')
    cwe_checker = models.BooleanField(
        help_text='Enables cwe-checker,-c will be added', default=False)
    docker_container = models.BooleanField(help_text='Run emba in docker container, -D will be added', default=False)
    deep_extraction = models.BooleanField(
        help_text='Enable deep extraction, -x will be added', default=False)
    log_path = models.BooleanField(help_text='Ignores log path check, -i will be added', default=False)
    grep_able_log = models.BooleanField(
        help_text='Create grep-able log file in [log_path]/fw_grep.log, -g will be added', default=False)
    relative_paths = models.BooleanField(
        help_text='Prints only relative paths, -s will be added', default=False)
    ANSI_color = models.BooleanField(help_text='Adds ANSI color codes to log, -z will be added', default=False)
    web_reporter = models.BooleanField(
        help_text='Activates web report creation in log path, -W will be added', default=False)
    emulation_test = models.BooleanField(
        help_text='Enables automated qemu emulation tests, -E will be added', default=False)

    def to_shell(self):
        path = f"{self.id}/{self.title}"
        command = f"{path}"
        if self.version:
            command = command + " -X " + str([self.version])
        if self.vendor:
            command = command + " -Y " + str([self.vendor])
        if self.device:
            command = command + " -Z " + str([self.device])
        if self.notes:
            command = command + " -N " + str([self.notes])
        if self.firmware_Architecture:
            command = command + " -a " + str([self.firmware_Architecture])
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
        command = command + " -t" # running emba
    return command
