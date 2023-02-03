# pylint: disable=W0602
# ignores no-assignment error since there is one!
import copy
import difflib
import pathlib
import re
import time
import logging
import rx
import rx.operators as ops

from inotify_simple import INotify, flags
from asgiref.sync import async_to_sync

from channels.layers import get_channel_layer
from django.conf import settings

from uploader.models import FirmwareAnalysis


logger = logging.getLogger(__name__)

# global map for storing messages from all processes
PROCESS_MAP = {}

# EMBAs module count
EMBA_S_MOD_CNT = 39
EMBA_P_MOD_CNT = 20
EMBA_F_MOD_CNT = 4
EMBA_L_MOD_CNT = 7
EMBA_MODULE_CNT = EMBA_S_MOD_CNT + EMBA_P_MOD_CNT + EMBA_F_MOD_CNT + EMBA_L_MOD_CNT

EMBA_PHASE_CNT = 4  # P, S, L, F modules
# EMBA states
EMBA_P_PHASE = 1
EMBA_S_PHASE = 2
EMBA_L_PHASE = 3
EMBA_F_PHASE = 4


class LogReader:
    # TODO fix!!!!
    # TODO send update on refresh!!!
    def __init__(self, firmware_id):

        # global module count and status_msg directory
        self.module_cnt = 0
        self.firmware_id = firmware_id
        self.firmware_id_str = str(self.firmware_id)
        try:
            self.firmwarefile = FirmwareAnalysis.objects.get(id=firmware_id).firmware.__str__()
        except Exception as error:
            logger.error("Firmware file exception: %s", error)

        # set variables for channels communication
        self.room_group_name = 'updatesgroup'
        self.channel_layer = get_channel_layer()

        # variables for cleanup
        self.finish = False
        # self.wd = None

        # for testing
        self.test_list1 = []
        self.test_list2 = []

        # status update dict (appended to processmap)
        self.status_msg = {
            "firmwarename": self.firmwarefile,
            "percentage": 0.0,
            "module": "",
            "phase": "",
        }

        # start processing
        time.sleep(1)
        if FirmwareAnalysis.objects.filter(id=self.firmware_id).exists():
            self.read_loop()
        else:
            self.cleanup()

    @staticmethod
    def phase_identify(status_message):
        # phase patterns to match
        pre_checker_phase_pattern = "Pre-checking phase"
        testing_phase_pattern = "Testing phase"
        simulation_phase_pattern = "System emulation phase"
        reporting_phase_pattern = "Reporting phase"
        done_pattern = "Test ended on"
        failed_pattern = "EMBA failed in docker mode!"

        # calculate percentage
        max_module = -1
        phase_nmbr = -1
        if re.search(pattern=re.escape(pre_checker_phase_pattern), string=status_message["phase"]):
            max_module = EMBA_P_MOD_CNT
            phase_nmbr = EMBA_P_PHASE
        elif re.search(pattern=re.escape(testing_phase_pattern), string=status_message["phase"]):
            max_module = EMBA_S_MOD_CNT
            phase_nmbr = EMBA_S_PHASE
        elif re.search(pattern=re.escape(simulation_phase_pattern), string=status_message["phase"]):
            max_module = EMBA_L_MOD_CNT
            phase_nmbr = EMBA_L_PHASE
        elif re.search(pattern=re.escape(reporting_phase_pattern), string=status_message["phase"]):
            max_module = EMBA_F_MOD_CNT
            phase_nmbr = EMBA_F_PHASE
        elif re.search(pattern=re.escape(done_pattern), string=status_message["phase"]):
            max_module = 0
            phase_nmbr = EMBA_PHASE_CNT
        elif re.search(pattern=re.escape(failed_pattern), string=status_message["phase"]):
            max_module = -2
            phase_nmbr = 0
        return max_module, phase_nmbr

    # update our dict whenever a new module is being processed
    def update_status(self, stream_item_list):
        percentage = 0
        max_module, phase_nmbr = self.phase_identify(self.status_msg)
        if max_module > 0:
            self.module_cnt += 1
            self.module_cnt = self.module_cnt % max_module  # make sure it's in range
            percentage = phase_nmbr * (100 / EMBA_PHASE_CNT) + ((100 / EMBA_PHASE_CNT) / max_module) * self.module_cnt   # increments: F=6.25, S=0.65, L=3.57, P=1.25
        elif max_module == 0:
            percentage = 100
        else:
            logger.error("EMBA failed")
            self.finish = True
            analysis = FirmwareAnalysis.objects.get(id=self.firmware_id)
            analysis.failed = True
            analysis.finished = True
            analysis.save()
            logger.debug("Undefined state in logreader %s ", self.status_msg)

        # smarty conversion
        percentage = percentage / 100

        # set attributes of current message
        self.status_msg["module"] = stream_item_list[0]
        self.status_msg["percentage"] = percentage

        # get copy of the current status message
        tmp_mes = copy.deepcopy(self.status_msg)

        # append it to the data structure
        global PROCESS_MAP
        if FirmwareAnalysis.objects.filter(id=self.firmware_id).exists():
            found = False
            for mes in PROCESS_MAP[self.firmware_id_str]:
                if mes["phase"] == tmp_mes["phase"] and mes["module"] == tmp_mes["module"]:
                    found = True

            if not found:
                PROCESS_MAP[self.firmware_id_str].append(tmp_mes)

                # send it to room group
                async_to_sync(self.channel_layer.group_send)(
                    self.room_group_name, {
                        "type": 'send.message',
                        "message": PROCESS_MAP
                    }
                )
        else:
            logger.error("Error in update_status, object with id=%s not found", self.firmware_id)

    # update dictionary with phase changes
    def update_phase(self, stream_item_list):
        self.module_cnt = 0
        self.status_msg["phase"] = stream_item_list[1]

        # get copy of the current status message
        tmp_mes = copy.deepcopy(self.status_msg)

        # append it to the data structure
        global PROCESS_MAP
        if FirmwareAnalysis.objects.filter(id=self.firmware_id).exists():
            found = False
            for mes in PROCESS_MAP[self.firmware_id_str]:
                if mes["phase"] == tmp_mes["phase"] and mes["module"] == tmp_mes["module"]:
                    found = True

            if not found:
                PROCESS_MAP[self.firmware_id_str].append(tmp_mes)

                # send it to room group
                async_to_sync(self.channel_layer.group_send)(
                    self.room_group_name, {
                        'type': 'send.message',
                        'message': PROCESS_MAP
                    }
                )
        else:
            logger.error("Error in update_phase, object with id=%s not found", self.firmware_id)
        if "Test ended" in stream_item_list[1]:
            self.finish = True

    def read_loop(self):
        """
        Infinite Loop for waiting for emba.log changes
            :param: None
            :exit condition: Not in this Function, but if emba has terminated this process is also killed
            :return: None
       """
        logger.info("read loop started for %s", self.firmware_id)

        while not self.finish:

            # get firmware for id which the BoundedExecutor gave the log_reader
            firmware = FirmwareAnalysis.objects.get(id=self.firmware_id)

            # if file does not exist create it otherwise delete its content
            pat = f"{settings.EMBA_LOG_ROOT}/{self.firmware_id}/logreader.log"
            if not pathlib.Path(pat).exists():
                with open(pat, 'w+', encoding='utf-8'):
                    pass

            # create an entry for the id in the process map
            global PROCESS_MAP
            if self.firmware_id_str not in PROCESS_MAP:
                PROCESS_MAP[self.firmware_id_str] = []

            # look for new events in log
            logger.debug("looking for events in %s", f"{firmware.path_to_logs}/emba.log")
            got_event = self.inotify_events(f"{firmware.path_to_logs}/emba.log")

            for eve in got_event:
                for flag in flags.from_mask(eve.mask):
                    # Ignore irrelevant flags TODO: add other possible flags
                    if flag is flags.CLOSE_NOWRITE or flag is flags.CLOSE_WRITE:
                        pass
                    # Act on file change
                    elif flag is flags.MODIFY:
                        # get the actual difference
                        tmp = self.get_diff(f"{firmware.path_to_logs}/emba.log")
                        # send changes to frontend
                        self.input_processing(tmp)
                        # copy diff to tmp file
                        self.copy_file_content(tmp)

        self.cleanup()
        logger.info("read loop done for %s", self.firmware_id)
        # return

    def cleanup(self):
        """
        Called when logreader should be cleaned up
        """
        # inotify = INotify()
        # inotify.rm_watch(self.wd)
        logger.debug("Log reader cleaned up for %s", self.firmware_id)
        # TODO do cleanup of emba_new_<self.firmware_id>.log

    @classmethod
    def process_line(cls, inp, pat):

        """
        Regex function for lambda
            :param inp: String to apply regex to
            :param pat: Regex pattern
            :return: True if regex matches otherwise False
        """

        if re.match(pat, inp):
            return True
        # else:
        return False

    def copy_file_content(self, diff):
        """
        Helper function to copy new emba log messages to temporary file continuously
            :param diff: new line in emba log
            :return: None
        """

        with open(f"{settings.EMBA_LOG_ROOT}/{self.firmware_id}/logreader.log", 'a+', encoding='utf-8') as diff_file:
            diff_file.write(diff)

    def get_diff(self, log_file):
        """
        Get diff between two files via difflib
        copied from stack overflow : https://stackoverflow.com/questions/15864641/python-difflib-comparing-files
            :param: None
            :return: result of difflib call without preceding symbols
        """

        # open the two files to get diff from
        logger.debug("getting diff from %s", log_file)
        with open(log_file, encoding='utf-8') as old_file, open(f"{settings.EMBA_LOG_ROOT}/{self.firmware_id}/logreader.log", encoding='utf-8') as new_file:
            diff = difflib.ndiff(old_file.readlines(), new_file.readlines())
            return ''.join(x[2:] for x in diff if x.startswith('- '))

    def input_processing(self, tmp_inp):
        """
        RxPy Function for processing the file diffs and trigger send packet to frontend
            :param tmp_inp: file diff = new line in emba log
            :return: None
        """

        status_pattern = "\\[\\*\\]*"
        phase_pattern = "\\[\\!\\]*"

        color_pattern = "\\x1b\\[.{1,5}m"

        cur_ar = tmp_inp.splitlines()

        # create observable
        source_stream = rx.from_iterable(cur_ar)

        # observer for status messages
        source_stream.pipe(
            ops.map(lambda s: re.sub(color_pattern, '', s)),
            ops.filter(lambda s: self.process_line(s, status_pattern)),
            ops.map(lambda a: a.split("- ")),
            ops.map(lambda t: t[1]),
            ops.map(lambda b: b.split(" ")),
            ops.filter(lambda c: c[1] == 'finished')
        ).subscribe(
            lambda x: [self.update_status(x)]    # , self.test_list1.append(x)]
        )

        # observer for phase messages
        source_stream.pipe(
            ops.map(lambda s: re.sub(color_pattern, '', s)),
            ops.filter(lambda u: self.process_line(u, phase_pattern)),
            ops.map(lambda v: v.split(" ", 1)),
            ops.filter(lambda w: w[1])
        ).subscribe(
            lambda x: [self.update_phase(x)]     # , self.test_list2.append(x)
        )

    @classmethod
    def inotify_events(cls, path):
        # def inotify_events(self, path):
        inotify = INotify()
        watch_flags = flags.CREATE | flags.DELETE | flags.MODIFY | flags.DELETE_SELF | flags.CLOSE_NOWRITE | flags.CLOSE_WRITE
        try:
            # add watch on file
            inotify.add_watch(path, watch_flags)
            return inotify.read()
        except Exception as error:
            logger.error("inotify_event error in %s:%s", path, error)
            return []

    def produce_test_output(self, inp):
        self.input_processing(inp)
        return self.test_list1, self.test_list2


if __name__ == "__main__":
    PHASE = "\\[\\!\\]*"
    test_dir = pathlib.Path(__file__).resolve().parent.parent.parent
    status_msg = {
        "firmwarename": "LogTestFirmware",
        "percentage": 0.0,
        "module": "",
        "phase": "",
    }

    with open(f"{test_dir}/test/logreader/test-run-good.log", 'r', encoding='UTF-8') as test_file:
        for line in test_file:
            if re.match(PHASE, line) is not None:
                status_msg["phase"] = line
            LogReader.phase_identify(status_msg)
