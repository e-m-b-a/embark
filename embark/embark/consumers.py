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
# from asgiref.sync import async_to_sync


# consumer class for synchronous websocket communication
class WSConsumer(WebsocketConsumer):

    def __init__(self):
        super().__init__()
        # self.room_group_name = 'status_updates_group'
        # global module count and status_msg directory
        self.module_count = 0
        self.status_msg = {
            "percentage": 0.0,
            "module": "",
            "phase": "",
        }

    def connect(self):
        self.accept()
        # print("HAAAAAAAAAAAAAAAALLLOO")
        open('/app/emba/log_1/emba_new.log', 'w+')
        self.read_loop()

    def receive(self, text_data=None, bytes_data=None):
        pass

    def disconnect(self, close_code):
        pass

    def send_data(self):
        # message = event['message']
        self.send(json.dumps(self.status_msg, sort_keys=True))

    # update our dict whenever a new module is being processed
    def update_status(self, stream_item_list):
        self.module_count += 1
        percentage = self.module_count / 35
        logging.error("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        logging.error(stream_item_list[0])
        self.status_msg.update({"module": stream_item_list[0]})
        self.status_msg.update({"percentage": percentage})

    # update our dict whenever a new phase is initiated
    def update_phase(self, stream_item_list):
        logging.error("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        logging.error(stream_item_list[1])
        self.status_msg.update({"phase": stream_item_list[1]})

    # loop for waiting for events
    def read_loop(self):
        while True:
            got_event = inotify_wrap.inotify_events()
            print(got_event)
            for eve in got_event:
                for flag in flags.from_mask(eve.mask):
                    print(flag)
                    if flag is flags.CLOSE_NOWRITE or flag is flags.CLOSE_WRITE:
                        pass
                    elif flag is flags.MODIFY:
                        tmp = self.get_diff()
                        self.input_processing(tmp)
                        self.copy_file_content(tmp)

    # regex function for lambda
    def process_line(self, inp, pat):
        if re.match(pat, inp):
            return True
        else:
            return False

    # copy content continuously
    def copy_file_content(self, diff):
        with open('/app/emba/log_1/emba_new.log', 'a') as diff_file:
            # read content from first file
            diff_file.write(diff)

    # copied from stack overflow : https://stackoverflow.com/questions/15864641/python-difflib-comparing-files
    # get diff between 2 files
    def get_diff(self):
        old_file = open('/app/emba/log_1/emba.log')
        new_file = open('/app/emba/log_1/emba_new.log')

        diff = difflib.ndiff(old_file.readlines(), new_file.readlines())
        return ''.join(x[2:] for x in diff if x.startswith('- '))

    # function for opening log file
    def input_processing(self, tmp_inp):
        status_pattern = "\[\*\]*"
        phase_pattern = "\[\!\]*"
        cur_ar = tmp_inp.splitlines()
        source_stream = rx.from_(cur_ar)

        source_stream.pipe(
            ops.filter(lambda s: self.process_line(s, status_pattern)),
            ops.map(lambda a: a.split("- ")),
            ops.map(lambda t: t[1]),
            ops.map(lambda b: b.split(" "))
        ).subscribe(
            lambda x: self.update_status(x)
        )

        source_stream.pipe(
            ops.filter(lambda u: self.process_line(u, phase_pattern)),
            ops.map(lambda v: v.split(" ", 1)),
            ops.filter(lambda w: w[1])
        ).subscribe(
            lambda x: self.update_phase(x)
        )
        self.send_data()

    # if __name__ == '__main__':
    #     open('/app/emba/logs/emba_new.log', 'w+')
    #     read_loop()
