from django.test import TestCase
from . import logreader
import logging

from uploader.models import Firmware, FirmwareFile

logger = logging.getLogger('web')


class test_logreader(TestCase):

    def setUp(self):
        self.log_string1 = "[\x1b[0;33m*\x1b[0m] Tue Jun 15 12:12:26 UTC 2021 - P02_firmware_bin_file_check starting\n"
        self.log_string2 = "[\x1b[0;33m*\x1b[0m] Tue Jun 15 12:12:27 UTC 2021 - P02_firmware_bin_file_check finished\n"
        self.log_string3 = "[\x1b[0;35m!\x1b[0m]\x1b[0;35m Test ended on Sat Jul  3 00:07:10 UTC 2021 and took about 00:34:24\x1b[0m\n"
        self.log_string4 = "[*] Wed Apr 21 15:32:46 UTC 2021 - P05_firmware_bin_extractor starting"
        self.log_list = []
        self.log_list.append(self.log_string1)
        self.log_list.append(self.log_string2)
        self.log_list.append(self.log_string3)
        self.log_list.append(self.log_string4)

        # creat DB entry
        test_file = FirmwareFile.objects.create()
        firmware = Firmware(firmware=test_file)
        firmware.pk = -1
        firmware.save()

    def test_in_pro(self):
        lr = logreader.LogReader(-1)
        res1 = []
        res2 = []
        for line in self.log_list:
            res1, res2 = lr.produce_test_output(line)
        self.assertEqual("P02_firmware_bin_file_check", res1[0][0])
        self.assertEqual("Test ended on Sat Jul  3 00:07:10 UTC 2021 and took about 00:34:24",
                         res2[0][1])
