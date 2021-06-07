from django.test import TestCase

from .models import Firmware


class test_models(TestCase):

    def setUp(self):
        self.fw_file = None

    # TODO: add timeout
    def test_get_flags_all_true(self):

        firmware = Firmware(firmware=self.fw_file)

        firmware.version = "version"
        firmware.vendor = "vendor"
        firmware.device = "device"
        firmware.notes = "notes"
        firmware.firmware_Architecture = "x64"
        firmware.cwe_checker = True
        firmware.docker_container = True
        firmware.deep_extraction = True
        firmware.log_path = True
        firmware.grep_able_log = True
        firmware.relative_paths = True
        firmware.ANSI_color = True
        firmware.web_reporter = True
        firmware.emulation_test = True
        firmware.dependency_check = True
        firmware.multi_threaded = True

        expected_string = " -X version -Y vendor -Z device -N notes -a x64 -c -D -x -i -g -s -z -W -E -F -t"
        self.assertEqual(firmware.get_flags(), expected_string)

    def test_get_flags_all_false(self):

        firmware = Firmware(firmware=self.fw_file)

        firmware.version = None
        firmware.vendor = None
        firmware.device = None
        firmware.notes = None
        firmware.firmware_Architecture = None
        firmware.cwe_checker = False
        firmware.docker_container = False
        firmware.deep_extraction = False
        firmware.log_path = False
        firmware.grep_able_log = False
        firmware.relative_paths = False
        firmware.ANSI_color = False
        firmware.web_reporter = False
        firmware.emulation_test = False
        firmware.dependency_check = False
        firmware.multi_threaded = False

        expected_string = ""
        self.assertEqual(firmware.get_flags(), expected_string)
