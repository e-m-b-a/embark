__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'Benedikt Kuehne, diegiesskanne, m-1-k-3, Maximilian Wagner, Ashutosh Singh'
__license__ = 'MIT'

import filecmp
import logging
import os
import time
import re
import uuid

from unittest import skipIf
from django.conf import settings
from django.test import TestCase
from uploader.models import FirmwareAnalysis

from embark.logreader import EMBA_F_PHASE, EMBA_L_PHASE, EMBA_P_PHASE, EMBA_PHASE_CNT, EMBA_S_PHASE, LogReader
from embark.helper import count_emba_modules, get_emba_modules

logger = logging.getLogger(__name__)

STATUS_PATTERN = r"\[\*\]*"
PHASE_PATTERN = r"\[\!\]*"
COLOR_PATTERN = '\033\\[([0-9]+)(;[0-9]+)*m'

S_MODULE_CNT = P_MODULE_CNT = Q_MODULE_CNT_ = L_MODULE_CNT = F_MODULE_CNT = D_MODULE_CNT_ = None


class LogreaderException(Exception):
    pass


@skipIf(os.environ.get('EMBA_INSTALL') == "no", "Skip tests depending on EMBA if not installed")
class TestLogreader(TestCase):

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.test_file_good = os.path.join(settings.BASE_DIR.parent, "test/logreader/good-log")
        self.test_file_bad = os.path.join(settings.BASE_DIR.parent, "test/logreader/fail-log")
        self.analysis_id = uuid.uuid4()

        emba_module_dict = get_emba_modules(settings.EMBA_ROOT)

        global S_MODULE_CNT, P_MODULE_CNT, Q_MODULE_CNT_, L_MODULE_CNT, F_MODULE_CNT, D_MODULE_CNT_
        S_MODULE_CNT, P_MODULE_CNT, Q_MODULE_CNT_, L_MODULE_CNT, F_MODULE_CNT, D_MODULE_CNT_ = count_emba_modules(emba_module_dict)

    def setUp(self):
        super().setUp()
        analysis = FirmwareAnalysis.objects.create(id=self.analysis_id)
        analysis.failed = False
        analysis.path_to_logs = f"{settings.EMBA_LOG_ROOT}/{analysis.id}/emba_logs"
        analysis.save()   # args??

        os.makedirs(f"{settings.EMBA_LOG_ROOT}", exist_ok=True)
        os.mkdir(f"{settings.EMBA_LOG_ROOT}/{self.analysis_id}")
        os.mkdir(f"{settings.EMBA_LOG_ROOT}/{self.analysis_id}/emba_logs")

        print("Testing on Analysis:%s", self.analysis_id)
        # check test_log file
        if not os.path.isfile(self.test_file_good) or not os.path.isfile(self.test_file_bad):
            logger.error("test_files not accessible")
            raise FileNotFoundError("Files for testing not found")

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
                    for _module in range(0, P_MODULE_CNT):
                        status_msg["percentage"] = self.logreader_status_calc(phase_identifier, module_count, _module) / 100
                        self.assertTrue(0 <= status_msg["percentage"] <= 25)
                elif phase_identifier == EMBA_S_PHASE:
                    for _module in range(0, S_MODULE_CNT):
                        status_msg["percentage"] = self.logreader_status_calc(phase_identifier, module_count, _module) / 100
                        self.assertTrue(0.25 <= status_msg["percentage"] <= 0.50)
                elif phase_identifier == EMBA_L_PHASE:
                    for _module in range(0, L_MODULE_CNT):
                        status_msg["percentage"] = self.logreader_status_calc(phase_identifier, module_count, _module) / 100
                        self.assertTrue(0.50 <= status_msg["percentage"] <= 0.75)
                elif phase_identifier == EMBA_F_PHASE:
                    for _module in range(0, F_MODULE_CNT):
                        status_msg["percentage"] = self.logreader_status_calc(phase_identifier, module_count, _module) / 100
                        self.assertTrue(0.75 <= status_msg["percentage"] <= 1.0)
                elif phase_identifier == EMBA_PHASE_CNT:
                    status_msg["percentage"] = 1.0
                    self.assertEqual(status_msg['percentage'], 1.0)
                elif phase_identifier < 0:
                    status_msg["percentage"] = self.logreader_status_calc(phase_identifier, module_count, 0) / 100
                    self.assertEqual(status_msg['percentage'], 0.0)
                else:
                    print("weird phase in logreader line: %s - phase: %s ", line, phase_identifier)
                    raise LogreaderException("Weird state in logreader")
            # file should be identical to emba.log
            self.assertTrue(filecmp.cmp(file, f"{settings.EMBA_LOG_ROOT}/{self.analysis_id}/emba_logs/emba.log"), "Files not equal?!")

    def write_to_log(self, line):
        """
        writes log line by line into log file
        """
        with open(f"{settings.EMBA_LOG_ROOT}/{self.analysis_id}/emba_logs/emba.log", 'a', encoding='UTF-8') as file:
            file.write(line)

    def test_logreader_with_files(self):
        print("Testing Logreader with 2 files")
        self.file_test(self.test_file_good)
        os.remove(f"{settings.EMBA_LOG_ROOT}/{self.analysis_id}/emba_logs/emba.log")
        # self.file_test(self.test_file_bad)
