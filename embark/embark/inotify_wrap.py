import os
from inotify_simple import INotify, flags


def inotify_events():
    inotify = INotify()
    watch_flags = flags.CREATE | flags.DELETE | flags.MODIFY | flags.DELETE_SELF | flags.CLOSE_NOWRITE | flags.CLOSE_WRITE

    inotify.add_watch('/app/emba/log_1/emba.log', watch_flags)
    return inotify.read()
