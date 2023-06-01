import filecmp
import logging
import os
import time
import re

from django.conf import settings
from django.test import TestCase
from uploader.models import FirmwareAnalysis

from embark.logreader import EMBA_F_PHASE, EMBA_L_PHASE, EMBA_P_PHASE, EMBA_S_PHASE, LogReader

logger = logging.getLogger(__name__)

STATUS_PATTERN = "\\[\\*\\]*"
PHASE_PATTERN = "\\[\\!\\]*"


class LogreaderException(Exception):
    pass


class TestLogreader(TestCase):

    def setUp(self):
        os.mkdir(f"{settings.EMBA_LOG_ROOT}")
        super().setUp()
        analysis = FirmwareAnalysis.objects.create()
        analysis.failed = False
        analysis.save()   # args??

        self.analysis_id = analysis.id
        os.mkdir(f"{settings.EMBA_LOG_ROOT}/{self.analysis_id}")

        self.test_file_good = os.path.join(settings.BASE_DIR.parent, "test/logreader/good-log")
        self.test_file_bad = os.path.join(settings.BASE_DIR.parent, "test/logreader/fail-log")
        # check test_log file
        if not os.path.isfile(self.test_file_good) or not os.path.isfile(self.test_file_bad):
            logger.error("test_files not accessable")
            print("Files for testing not found")

    def file_test(self, file):
        logr = LogReader(self.analysis_id)
        # global PROCESS_MAP
        with open(file, 'r', encoding='UTF-8') as test_file:
            for line in test_file:
                self.write_to_log(line)   # simulates EMBA
                time.sleep(0.1)
                # message check
                # print("PROCESSMAP with index %s looks like this:%s", str(self.analysis_id), PROCESS_MAP[str(self.analysis_id)])
                self.assertTrue(filecmp.cmp(f"{settings.EMBA_LOG_ROOT}/{self.analysis_id}/logreader.log", f"{settings.EMBA_LOG_ROOT}/{self.analysis_id}/emba_logs/emba.log"), "Files not equal?!")   # check correctness of regexes
                if re.match(STATUS_PATTERN, line):
                    self.assertEqual(logr.status_msg['status'], line)
                elif re.match(PHASE_PATTERN, line):
                    self.assertEqual(logr.status_msg['phase'], line)
                else:
                    print("weird line in logreader: %s", line)
                _, phase_identifier = logr.phase_identify(logr.status_msg)
                if phase_identifier == EMBA_P_PHASE:
                    self.assertGreaterEqual(logr.status_msg['percentage'], 0.0)
                elif phase_identifier == EMBA_S_PHASE:
                    self.assertGreaterEqual(logr.status_msg['percentage'], 0.25)
                elif phase_identifier == EMBA_L_PHASE:
                    self.assertGreaterEqual(logr.status_msg['percentage'], 0.50)
                elif phase_identifier == EMBA_F_PHASE:
                    self.assertGreaterEqual(logr.status_msg['percentage'], 0.75)
                elif phase_identifier in (0, 4):
                    self.assertEqual(logr.status_msg['percentage'], 1.0)
                elif phase_identifier < 0:
                    self.assertEqual(logr.status_msg['percentage'], 0.0)
                else:
                    print("weird phase in logreader line: %s - phase: %s ", line, phase_identifier)
                    raise LogreaderException("Weird state in logreader")
            # logreader file should be identical to emba.log
            self.assertEqual(logr.finish, True)

    def write_to_log(self, line):
        """
        writes log line by line into log file
        """
        with open(f"{settings.EMBA_LOG_ROOT}/{self.analysis_id}/emba_logs/emba.log", 'w', encoding='UTF-8') as file:
            file.write(line)

    def test_logreader_with_files(self):
        self.file_test(self.test_file_bad)
        os.remove(f"{settings.EMBA_LOG_ROOT}/{self.analysis_id}/logreader.log")
        os.remove(f"{settings.EMBA_LOG_ROOT}/{self.analysis_id}/emba_logs/emba.log")
        self.file_test(self.test_file_good)
