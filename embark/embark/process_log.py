# import os
#
# import channels
# import rx
# from rx import Observable
# import rx.operators as ops
# import re
# from inotify_simple import INotify, flags
# import inotify_wrap
# import difflib
# from channels.layers import get_channel_layer
# from asgiref.sync import async_to_sync
#
# # global module count and status_msg directory
# module_count = 0
# status_msg = {
#         "percentage": 0.0,
#         "module": "",
#         "phase": "",
#     }
#
#
# # update our dict whenever a new module is being processed
# def update_status(stream_item_list):
#     global module_count
#     module_count += 1
#     percentage = module_count / 35
#
#     status_msg.update({"module": stream_item_list[0]})
#     status_msg.update({"percentage": percentage})
#
#
# # update our dict whenever a new phase is initiated
# def update_phase(stream_item_list):
#     status_msg.update({"phase": stream_item_list[1]})
#
#
# # def event_trigger():
# #     channel_layer = channels.layers.get_channel_layer()
# #     async_to_sync(channel_layer.group_send)(
# #         'status_updates_group',
# #         {
# #             'type': 'send_data',
# #             'message': status_msg
# #         }
# #     )
#
#
# # loop for waiting for events
# def read_loop():
#     while True:
#         got_event = inotify_wrap.inotify_events()
#         print(got_event)
#         for eve in got_event:
#             for flag in flags.from_mask(eve.mask):
#                 print(flag)
#                 if flag is flags.CLOSE_NOWRITE or flag is flags.CLOSE_WRITE:
#                     pass
#                 elif flag is flags.MODIFY:
#                     tmp = get_diff()
#                     input_processing(tmp)
#                     copy_file_content(tmp)
#
#
# # regex function for lambda
# def process_line(inp, pat):
#     if re.match(pat, inp):
#         return True
#     else:
#         return False
#
#
# # copy content continuously
# def copy_file_content(diff):
#     with open('/app/emba/logs/emba_new.log', 'a') as diff_file:
#         # read content from first file
#         diff_file.write(diff)
#
#
# # copied from stack overflow : https://stackoverflow.com/questions/15864641/python-difflib-comparing-files
# # get diff between 2 files
# def get_diff():
#     old_file = open('/app/emba/logs/emba.log')
#     new_file = open('/app/emba/logs/emba_new.log')
#
#     diff = difflib.ndiff(old_file.readlines(), new_file.readlines())
#     return ''.join(x[2:] for x in diff if x.startswith('- '))
#
#
# # function for opening log file
# def input_processing(tmp_inp):
#     status_pattern = "\[\*\]*"
#     phase_pattern = "\[\!\]*"
#     cur_ar = tmp_inp.splitlines()
#     source_stream = rx.from_(cur_ar)
#
#     source_stream.pipe(
#         ops.filter(lambda s: process_line(s, status_pattern)),
#         ops.map(lambda a: a.split("- ")),
#         ops.map(lambda t: t[1]),
#         ops.map(lambda b: b.split(" "))
#     ).subscribe(
#         lambda x: update_status(x)
#     )
#
#     source_stream.pipe(
#         ops.filter(lambda u: process_line(u, phase_pattern)),
#         ops.map(lambda v: v.split(" ", 1)),
#         ops.filter(lambda w: w[1])
#     ).subscribe(
#         lambda x: update_phase(x)
#     )
#
#     #event_trigger()
#
#
# if __name__ == '__main__':
#     # os.environ.setdefault('SETTINGS_MODULE', 'embark.settings')
#     open('/app/emba/logs/emba_new.log', 'w+')
#     read_loop()
