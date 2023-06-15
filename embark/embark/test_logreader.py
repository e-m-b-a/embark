import filecmp
import logging
import os
import time
import re

from django.conf import settings
from django.test import TestCase
from uploader.models import FirmwareAnalysis

from embark.logreader import EMBA_F_MOD_CNT, EMBA_F_PHASE, EMBA_L_MOD_CNT, EMBA_L_PHASE, EMBA_P_MOD_CNT, EMBA_P_PHASE, EMBA_PHASE_CNT, EMBA_S_MOD_CNT, EMBA_S_PHASE, LogReader

logger = logging.getLogger(__name__)

STATUS_PATTERN = r"\[\*\]*"
PHASE_PATTERN = r"\[\!\]*"
COLOR_PATTERN = '\033\\[([0-9]+)(;[0-9]+)*m'


class LogreaderException(Exception):
    pass


class TestLogreader(TestCase):

    def setUp(self):
        super().setUp()
        analysis = FirmwareAnalysis.objects.create()
        analysis.failed = False
        analysis.path_to_logs = f"{settings.EMBA_LOG_ROOT}/{analysis.id}/emba_logs"
        analysis.save()   # args??

        self.analysis_id = analysis.id
        os.makedirs(f"{settings.EMBA_LOG_ROOT}", exist_ok=True)
        os.mkdir(f"{settings.EMBA_LOG_ROOT}/{self.analysis_id}")
        os.mkdir(f"{settings.EMBA_LOG_ROOT}/{self.analysis_id}/emba_logs")

        print("Testing on Analysis:%s", self.analysis_id)
        self.test_file_good = os.path.join(settings.BASE_DIR.parent, "test/logreader/good-log")
        self.test_file_bad = os.path.join(settings.BASE_DIR.parent, "test/logreader/fail-log")
        # check test_log file
        if not os.path.isfile(self.test_file_good) or not os.path.isfile(self.test_file_bad):
            logger.error("test_files not accessible")
            raise Exception("Files for testing not found")
        
    @staticmethod
    def logreader_status_calc(phase_nmbr, max_module, module_cnt):
        return phase_nmbr * (100 / EMBA_PHASE_CNT) + ((100 / EMBA_PHASE_CNT) / max_module) * module_cnt
    
    def file_test(self, file):
        status_msg = {
            "firmwarename": "LogTestFirmware",
            "percentage": 0,
            "module": "",
            "phase": "",
        }
        # global PROCESS_MAP
        with open(file, 'r', encoding='UTF-8') as test_file:
            for line in test_file:
                self.write_to_log(line)   # simulates EMBA
                time.sleep(0.1)
                # message check
                # print("PROCESSMAP with index %s looks like this:%s", str(self.analysis_id), PROCESS_MAP[str(self.analysis_id)])
                re.sub(COLOR_PATTERN, '', line)
                if re.match(STATUS_PATTERN, line):
                    status_msg["module"] = line
                elif re.match(PHASE_PATTERN, line):
                    status_msg["phase"] = line
                else:
                    print("weird line in logreader: ", line)

                module_count, phase_identifier = LogReader.phase_identify(status_msg)
                if phase_identifier == EMBA_P_PHASE:
                    for _module in range(0, EMBA_P_MOD_CNT):
                        status_msg["percentage"] = self.logreader_status_calc(phase_identifier, module_count, _module) / 100
                        self.assertTrue(0 <= status_msg["percentage"] <= 25 )
                elif phase_identifier == EMBA_S_PHASE:
                    for _module in range(0, EMBA_S_MOD_CNT):
                        status_msg["percentage"] = self.logreader_status_calc(phase_identifier, module_count, _module) / 100
                        self.assertTrue(0.25 <= status_msg["percentage"] <= 0.50 )
                elif phase_identifier == EMBA_L_PHASE:
                    for _module in range(0, EMBA_L_MOD_CNT):
                        status_msg["percentage"] = self.logreader_status_calc(phase_identifier, module_count, _module) / 100
                        self.assertTrue(0.50 <= status_msg["percentage"] <= 0.75 )
                elif phase_identifier == EMBA_F_PHASE:
                    for _module in range(0, EMBA_F_MOD_CNT):
                        status_msg["percentage"] = self.logreader_status_calc(phase_identifier, module_count, _module) / 100
                        self.assertTrue(0.75 <= status_msg["percentage"] <= 1.0 )
                elif phase_identifier < 0:
                    status_msg["percentage"] = self.logreader_status_calc(phase_identifier, module_count, 0) / 100
                    self.assertEqual(status_msg['percentage'], 0.0)
                else:
                    print("weird phase in logreader line: %s - phase: %s ", line, phase_identifier)
                    raise LogreaderException("Weird state in logreader")
            # logreader file should be identical to emba.log
            self.assertEqual(status_msg["percentage"], 1.0)
            self.assertTrue(filecmp.cmp(file, f"{settings.EMBA_LOG_ROOT}/{self.analysis_id}/emba_logs/emba.log"), "Files not equal?!")

    def write_to_log(self, line):
        """
        writes log line by line into log file
        """
        with open(f"{settings.EMBA_LOG_ROOT}/{self.analysis_id}/emba_logs/emba.log", 'w', encoding='UTF-8') as file:
            file.write(line)

    def test_logreader_with_files(self):
        print("Testing Logreader with 2 files")
        self.file_test(self.test_file_good)
        os.remove(f"{settings.EMBA_LOG_ROOT}/{self.analysis_id}/emba_logs/emba.log")
        # self.file_test(self.test_file_bad)
