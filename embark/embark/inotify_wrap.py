import os
from inotify_simple import INotify, flags


def inotify_events():
    inotify = INotify()
    watch_flags = flags.CREATE | flags.DELETE | flags.MODIFY | flags.DELETE_SELF
    wd = inotify.add_watch('/app/emba/logs/emba.log', watch_flags)

    for event in inotify.read():
        print(event)
        for flag in flags.from_mask(event.mask):
            print('    ' + str(flag))
