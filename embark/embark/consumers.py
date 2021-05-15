import json
import logging

import os
import channels
import rx
from rx import Observable
import rx.operators as ops
import re
from inotify_simple import flags
from . import inotify_wrap
import difflib
from channels.generic.websocket import WebsocketConsumer
from pathlib import Path


# consumer class for synchronous/asynchronous websocket communication
# TODO: Implement frontend Websocket handling and data extraction (Example in progress.html -> remove later)
class WSConsumer(WebsocketConsumer):

    # constructor
    def __init__(self):
        super().__init__()
        # self.room_group_name = 'status_updates_group'
        # global module count and status_msg directory
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
        open('/app/emba/log_1/emba_new.log', 'w+')

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
        self.send(json.dumps(self.status_msg, sort_keys=True))

    # update our dict whenever a new module is being processed
    def update_status(self, stream_item_list):
        # progress percentage TODO: improve percentage calculation
        self.module_count += 1
        percentage = self.module_count / 35
        self.status_msg.update({"module": stream_item_list[0]})
        self.status_msg.update({"percentage": percentage})

    # update dictionary with phase changes
    def update_phase(self, stream_item_list):
        self.status_msg.update({"phase": stream_item_list[1]})

    """
              Infinite Loop for waiting for emba.log changes
              :param: None
              :exit condition: Not in this Function, but if emba.sh has terminated this process is also killed
              :return: None
    """

    def read_loop(self):
        while True:
            # look for new events
            got_event = inotify_wrap.inotify_events()
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

    """
              Regex function for lambda
              :param inp: String to apply regex to
              :param pat: Regex pattern
              :return: True if regex matches otherwise False
    """

    def process_line(self, inp, pat):
        if re.match(pat, inp):
            return True
        else:
            return False

    """
              Helper function to copy new emba log messages to temporary file continuously
              :param diff: new line in emba log
              :return: None
    """

    def copy_file_content(self, diff):
        with open('/app/emba/log_1/emba_new.log', 'a') as diff_file:
            diff_file.write(diff)

    """
              Get diff between two files via difflib
              copied from stack overflow : https://stackoverflow.com/questions/15864641/python-difflib-comparing-files
              :param: None
              :return: result of difflib call without preceding symbols
    """

    def get_diff(self):
        # open the two files to get diff from TODO: remove hard coding
        old_file = open('/app/emba/log_1/emba.log')
        new_file = open('/app/emba/log_1/emba_new.log')

        diff = difflib.ndiff(old_file.readlines(), new_file.readlines())
        return ''.join(x[2:] for x in diff if x.startswith('- '))

    """
              RxPy Function for processing the file diffs and trigger send packet to frontend
              :param tmp_inp: file diff = new line in emba log
              :return: None
    """

    def input_processing(self, tmp_inp):
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
            ops.map(lambda b: b.split(" "))
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
