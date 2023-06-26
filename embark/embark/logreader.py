# pylint: disable=W0602
# ignores no-assignment error since there is one!
import builtins
import datetime
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

# EMBAs module count
# TODO make this a settings var that gets set by counting on startup!
EMBA_S_MOD_CNT = 44
EMBA_P_MOD_CNT = 18
EMBA_F_MOD_CNT = 4
EMBA_L_MOD_CNT = 8
EMBA_MODULE_CNT = EMBA_S_MOD_CNT + EMBA_P_MOD_CNT + EMBA_F_MOD_CNT + EMBA_L_MOD_CNT

EMBA_PHASE_CNT = 4  # P, S, L, F modules
# EMBA states
EMBA_P_PHASE = 0
EMBA_S_PHASE = 1
EMBA_L_PHASE = 2
EMBA_F_PHASE = 3


class LogReader:
    def __init__(self, firmware_id):

        # global module count and status_msg directory
        self.module_cnt = 0
        self.firmware_id = firmware_id
        self.firmware_id_str = str(self.firmware_id)
        try:
            self.analysis = FirmwareAnalysis.objects.get(id=self.firmware_id)
        except FirmwareAnalysis.DoesNotExist:
            logger.error("No Analysis wit this id (%s)", self.firmware_id_str)

        # set variables for channels communication
        self.user = self.analysis.user
        self.room_group_name = f"services_{self.user}"
        self.channel_layer = get_channel_layer()

        # variables for cleanup
        self.finish = False
        # self.wd = None

        # status update dict (appended to db)
        self.status_msg = {
            "percentage": 0,
            "module": "",
            "phase": "",
        }

        # start processing
        time.sleep(10)   # embas dep-check takes some time
        if self.analysis:
            self.read_loop()
        else:
            self.cleanup()

    def save_status(self):
        logger.debug("Appending status with message: %s", self.status_msg)
        # append message to the json-field structure of the analysis
        self.analysis.status["percentage"] = self.status_msg["percentage"]
        self.analysis.status["last_update"] = str(datetime.datetime.now())
        # append modules and phase list
        if self.status_msg["module"] != self.analysis.status["last_module"]:
            self.analysis.status["last_module"] = self.status_msg["module"]
            self.analysis.status["module_list"].append(self.status_msg["module"])
        if self.status_msg["phase"] != self.analysis.status["last_phase"]:
            self.analysis.status["last_phase"] = self.status_msg["phase"]
            self.analysis.status["phase_list"].append(self.status_msg["phase"])
        if self.status_msg["percentage"] == 100:
            self.analysis.status["finished"] = True
            self.analysis.save(update_fields=["status"], force_update=True)
        else:
            self.analysis.save(update_fields=["status"])
        logger.debug("Checking status: %s", self.analysis.status)
        # send it to group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name, {
                "type": 'send.message',
                "message": {str(self.analysis.id): self.analysis.status}
            }
        )

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
            phase_nmbr = EMBA_PHASE_CNT
        return max_module, phase_nmbr

    # update our dict whenever a new module is being processed
    def update_status(self, stream_item_list):
        percentage = 0
        max_module, phase_nmbr = self.phase_identify(self.status_msg)
        if max_module == 0:
            percentage = 100
            self.finish = True
        elif max_module > 0:
            self.module_cnt += 1
            self.module_cnt = self.module_cnt % max_module  # make sure it's in range
            percentage = phase_nmbr * (100 / EMBA_PHASE_CNT) + ((100 / EMBA_PHASE_CNT) / max_module) * self.module_cnt   # increments: F=6.25, S=0.65, L=3.57, P=1.25
        else:
            logger.debug("Undefined state in logreader %s ", self.status_msg)

        logger.debug("Status is %d, in phase %d, with modules %d", percentage, phase_nmbr, max_module)

        # set attributes of current message
        self.status_msg["module"] = stream_item_list[0]
        # ignore all Q-modules for percentage calc
        if not re.match(".*Q[0-9][0-9]", stream_item_list[0]):
            self.status_msg["percentage"] = percentage

        # get copy of the current status message
        self.save_status()

    # update dictionary with phase changes
    def update_phase(self, stream_item_list):
        self.module_cnt = 0
        self.status_msg["phase"] = stream_item_list[1]
        if "Test ended" in stream_item_list[1]:
            self.finish = True
            self.status_msg["percentage"] = 100

        # get copy of the current status message
        self.save_status()

    def read_loop(self):
        """
        Infinite Loop for waiting for emba.log changes
            :param: None
            :exit condition: Not in this Function, but if emba has terminated this process is also killed
            :return: None
       """
        logger.info("read loop started for %s", self.firmware_id)

        # if file does not exist create it otherwise delete its content
        pat = f"{settings.EMBA_LOG_ROOT}/{self.firmware_id}/logreader.log"
        if not pathlib.Path(pat).exists():
            with open(pat, 'x', encoding='utf-8'):
                pass

        while not self.finish:
            # look for new events in log
            logger.debug("looking for events in %s", f"{self.analysis.path_to_logs}/emba.log")
            got_event = self.inotify_events(f"{self.analysis.path_to_logs}/emba.log")

            for eve in got_event:
                for flag in flags.from_mask(eve.mask):
                    # Ignore irrelevant flags TODO: add other possible flags
                    if flag is flags.CLOSE_NOWRITE or flag is flags.CLOSE_WRITE:
                        pass
                    # Act on file change
                    elif flag is flags.MODIFY:
                        # get the actual difference
                        tmp = self.get_diff(f"{self.analysis.path_to_logs}/emba.log")
                        logger.debug("Got diff-output: %s", tmp)
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
        logger.debug("wrote file-diff")

    def get_diff(self, log_file):
        """
        Get diff between two files via difflib
        copied from stack overflow : https://stackoverflow.com/questions/15864641/python-difflib-comparing-files
            :param: None
            :return: result of difflib call without preceding symbols
        """
        # open the two files to get diff from
        logger.debug("getting diff from %s", log_file)
        with open(log_file, mode='r', encoding='utf-8') as old_file, open(f"{settings.EMBA_LOG_ROOT}/{self.firmware_id}/logreader.log", encoding='utf-8') as new_file:
            diff = difflib.ndiff(old_file.readlines(), new_file.readlines())
            return ''.join(x[2:] for x in diff if x.startswith('- '))

    def input_processing(self, tmp_inp):
        """
        RxPy Function for processing the file diffs and trigger send packet to frontend
            :param tmp_inp: file diff = new line in emba log
            :return: None
        """
        logger.debug("starting observers for log file %s", self.analysis.path_to_logs)

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
        inotify = INotify()
        watch_flags = flags.CREATE | flags.DELETE | flags.MODIFY | flags.DELETE_SELF | flags.CLOSE_NOWRITE | flags.CLOSE_WRITE
        try:
            # add watch on file
            inotify.add_watch(path, watch_flags)
            return inotify.read()
        except builtins.Exception as error:
            logger.error("inotify_event error in %s:%s", path, error)
            return []


if __name__ == "__main__":
    PHASE = "\\[\\!\\]*"
    test_dir = pathlib.Path(__file__).resolve().parent.parent.parent
    status_msg = {
        "firmwarename": "LogTestFirmware",
        "percentage": 0,
        "module": "",
        "phase": "",
    }

    with open(f"{test_dir}/test/logreader/test-run-good.log", 'r', encoding='UTF-8') as test_file:
        for line in test_file:
            if re.match(PHASE, line) is not None:
                status_msg["phase"] = line
            LogReader.phase_identify(status_msg)
