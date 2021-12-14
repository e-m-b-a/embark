from django.test import TestCase

from .models import Firmware, FirmwareFile


class TestModels(TestCase):

    def __init__(self, *args, **kwargs):
        self.fw_file = FirmwareFile.objects.create()
        self.fw_file.save()

    # TODO: add timeout
    def test_get_flags_all_true(self):
        """
        test get_flags() if all flags set to String/True
        """

        firmware = Firmware(firmware=self.fw_file)

        firmware.version = "version"
        firmware.vendor = "vendor"
        firmware.device = "device"
        firmware.notes = "notes"
        firmware.firmware_Architecture = "x64"
        firmware.cwe_checker = True
        firmware.dev_mode = True
        firmware.deep_extraction = True
        firmware.log_path = True
        firmware.grep_able_log = True
        firmware.relative_paths = True
        firmware.ANSI_color = True
        firmware.web_reporter = True
        firmware.emulation_test = True
        firmware.dependency_check = True
        firmware.multi_threaded = True
        firmware.firmware_remove = True

        expected_string = " -X version -Y vendor -Z device -N notes -a x64 -c -D -x -i -g -s -z -W -E -F -t -r"
        self.assertEqual(firmware.get_flags(), expected_string)

    def test_get_flags_all_false(self):
        """
        test get_flags() if all flags set to None/False
        """

        firmware = Firmware(firmware=self.fw_file)

        firmware.version = None
        firmware.vendor = None
        firmware.device = None
        firmware.notes = None
        firmware.firmware_Architecture = None
        firmware.cwe_checker = False
        firmware.dev_mode = False
        firmware.deep_extraction = False
        firmware.log_path = False
        firmware.grep_able_log = False
        firmware.relative_paths = False
        firmware.ANSI_color = False
        firmware.web_reporter = False
        firmware.emulation_test = False
        firmware.dependency_check = False
        firmware.multi_threaded = False
        firmware.firmware_remove = False

        expected_string = ""
        self.assertEqual(firmware.get_flags(), expected_string)
