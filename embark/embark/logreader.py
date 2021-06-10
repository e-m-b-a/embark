import difflib
import re

import rx
import rx.operators as ops
import logging

from channels.generic.websocket import WebsocketConsumer

from django.conf import settings
from uploader.models import Firmware
from inotify_simple import INotify, flags
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger('web')


class LogReader:

    def __init__(self, firmware_id):
        super().__init__()
        # self.room_group_name = 'status_updates_group'
        # global module count and status_msg directory
        self.module_count = 0
        self.firmware_id = firmware_id
        self.room_group_name = 'updatesgroup'
        self.channel_layer = get_channel_layer()
        self.status_msg = {
            "percentage": 0.0,
            "module": "",
            "phase": "",
        }
        # self.channel_layer = get_channel_layer()
        self.process_map = {}
        # start processing
        self.read_loop()

    # update our dict whenever a new module is being processed
    def update_status(self, stream_item_list):
        # progress percentage TODO: improve percentage calculation
        self.module_count += 1
        percentage = self.module_count / 35
        self.status_msg["module"] = stream_item_list[0]
        self.status_msg["percentage"] = percentage
        tmp_mes = self.status_msg
        self.process_map[self.firmware_id].append(tmp_mes)
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name, {
                "type": 'send.message',
                "message": self.process_map
            }
        )

    # update dictionary with phase changes
    def update_phase(self, stream_item_list):
        self.status_msg["phase"] = stream_item_list[1]
        tmp_mes = self.status_msg
        self.process_map[self.firmware_id].append(tmp_mes)
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name, {
                'type': 'send.message',
                'message': self.process_map
            }
        )

    def read_loop(self):

        """
                 Infinite Loop for waiting for emba.log changes
                 :param: None
                 :exit condition: Not in this Function, but if emba.sh has terminated this process is also killed
                 :return: None
       """
        while True:
            # logger.debug(process_map)
            firmware = Firmware.objects.get(pk=self.firmware_id)
            open(f"{firmware.path_to_logs}/emba_new.log", 'w+')
            # logger.debug(firmware)
            if firmware.id not in self.process_map.keys():
                # if file does not exist create it otherwise delete its content
                self.process_map[firmware.id] = []

            # look for new events
            got_event = self.inotify_events(f"{firmware.path_to_logs}/emba.log")
            for eve in got_event:
                for flag in flags.from_mask(eve.mask):
                    # Ignore irrelevant flags TODO: add other possible flags
                    if flag is flags.CLOSE_NOWRITE or flag is flags.CLOSE_WRITE:
                        pass
                    # Act on file change
                    elif flag is flags.MODIFY:
                        # get the actual difference
                        tmp = self.get_diff(firmware.path_to_logs)
                        # send changes to frontend
                        self.input_processing(tmp)
                        # copy diff to tmp file
                        self.copy_file_content(tmp, firmware.path_to_logs)

    def process_line(self, inp, pat):

        """
                  Regex function for lambda
                  :param inp: String to apply regex to
                  :param pat: Regex pattern
                  :return: True if regex matches otherwise False
        """

        if re.match(pat, inp):
            return True
        else:
            return False

    def copy_file_content(self, diff, log_path):

        """
                  Helper function to copy new emba log messages to temporary file continuously
                  :param diff: new line in emba log
                  :return: None
        """

        with open(f"{log_path}/emba_new.log", 'a+') as diff_file:
            diff_file.write(diff)

    def get_diff(self, log_path):

        """
                  Get diff between two files via difflib
                  copied from stack overflow : https://stackoverflow.com/questions/15864641/python-difflib-comparing-files
                  :param: None
                  :return: result of difflib call without preceding symbols
        """

        # open the two files to get diff from
        old_file = open(f"{log_path}/emba.log")
        new_file = open(f"{log_path}/emba_new.log")

        diff = difflib.ndiff(old_file.readlines(), new_file.readlines())
        return ''.join(x[2:] for x in diff if x.startswith('- '))

    def input_processing(self, tmp_inp):

        """
                  RxPy Function for processing the file diffs and trigger send packet to frontend
                  :param tmp_inp: file diff = new line in emba log
                  :return: None
        """

        status_pattern = "\[\*\]*"
        phase_pattern = "\[\!\]*"

        color_pattern = "\\x1b\[.{1,5}m"

        cur_ar = tmp_inp.splitlines()

        # create observable
        source_stream = rx.from_(cur_ar)

        # observer for status messages
        source_stream.pipe(
            ops.map(lambda s: re.sub(color_pattern, '', s)),
            ops.filter(lambda s: self.process_line(s, status_pattern)),
            ops.map(lambda a: a.split("- ")),
            ops.map(lambda t: t[1]),
            ops.map(lambda b: b.split(" ")),
            ops.filter(lambda c: c[1] == 'finished')
        ).subscribe(
            lambda x: self.update_status(x)
        )

        # observer for phase messages
        source_stream.pipe(
            ops.map(lambda s: re.sub(color_pattern, '', s)),
            ops.filter(lambda u: self.process_line(u, phase_pattern)),
            ops.map(lambda v: v.split(" ", 1)),
            ops.filter(lambda w: w[1])
        ).subscribe(
            lambda x: self.update_phase(x)
        )

        # TODO: add more observers for more information
        # TODO: trigger send data maybe in another place

    def inotify_events(self, path):
        inotify = INotify()
        # TODO: add/remove flags to watch
        watch_flags = flags.CREATE | flags.DELETE | flags.MODIFY | flags.DELETE_SELF | flags.CLOSE_NOWRITE | flags.CLOSE_WRITE
        try:
            # add watch on file
            inotify.add_watch(path, watch_flags)
            return inotify.read()
        except:
            return []
