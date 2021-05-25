import difflib
import json
import logging
import os
import re
import sys

import rx
import rx.operators as ops
from channels.generic.websocket import WebsocketConsumer
from inotify_simple import flags
from django.conf import settings
from uploader import models


from . import inotify_wrap


# consumer class for synchronous/asynchronous websocket communication
# TODO: Implement frontend Websocket handling and data extraction (Example in progress.html -> remove later)


class WSConsumer(WebsocketConsumer):

    # constructor
    def __init__(self):
        super().__init__()
        # self.room_group_name = 'status_updates_group'
        # global module count and status_msg directory
        self.path = f"/app/emba/{settings.LOG_ROOT}/emba.log"
        self.path_new = f"/app/emba/{settings.LOG_ROOT}/emba_new.log"
        self.module_count = 0
        # TODO: extend dictionary for more information
        self.status_msg = {
            "percentage": 0.0,
            "module": "",
            "phase": "",
        }

    # this method is executed when the connection to the frontend is established
    def connect(self):
        # accept socket connection
        self.accept()

        # if file does not exist create it otherwise delete its content

        open(self.path_new, 'w+')

        # start waiting for events
        self.read_loop()

    # called when received data from frontend TODO: implement this for processing client input at backend
    def receive(self, text_data=None, bytes_data=None):
        pass

    # called when websocket connection is closed TODO: implement connection close if necessary
    def disconnect(self, close_code):
        pass

    # send data to frontend
    def send_data(self):
        self.send(json.dumps(self.status_msg, sort_keys=False))

    # update our dict whenever a new module is being processed
    def update_status(self, stream_item_list):
        # progress percentage TODO: improve percentage calculation
        self.module_count += 1
        percentage = self.module_count / 34
        self.status_msg["module"] = stream_item_list[0]
        self.status_msg["percentage"] = percentage

    # update dictionary with phase changes
    def update_phase(self, stream_item_list):
        self.status_msg["phase"] = stream_item_list[1]

    def read_loop(self):

        """
                 Infinite Loop for waiting for emba.log changes
                 :param: None
                 :exit condition: Not in this Function, but if emba.sh has terminated this process is also killed
                 :return: None
       """

        while True:

            # look for new events
            got_event = inotify_wrap.inotify_events(self.path)
            for eve in got_event:
                for flag in flags.from_mask(eve.mask):
                    # Ignore irrelevant flags TODO: add other possible flags
                    if flag is flags.CLOSE_NOWRITE or flag is flags.CLOSE_WRITE:
                        pass
                    # Act on file change
                    elif flag is flags.MODIFY:
                        # get the actual difference
                        tmp = self.get_diff()
                        # send changes to frontend
                        self.input_processing(tmp)
                        # copy diff to tmp file
                        self.copy_file_content(tmp)

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

    def copy_file_content(self, diff):

        """
                  Helper function to copy new emba log messages to temporary file continuously
                  :param diff: new line in emba log
                  :return: None
        """

        with open(self.path_new, 'a') as diff_file:
            diff_file.write(diff)

    def get_diff(self):

        """
                  Get diff between two files via difflib
                  copied from stack overflow : https://stackoverflow.com/questions/15864641/python-difflib-comparing-files
                  :param: None
                  :return: result of difflib call without preceding symbols
        """

        # open the two files to get diff from TODO: remove hard coding
        old_file = open(self.path)
        new_file = open(self.path_new)

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

        # trigger send to frontend
        self.send_data()