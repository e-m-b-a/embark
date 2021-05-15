import os
from inotify_simple import INotify, flags


# wrapper for inotify system call -> get notification on file change
def inotify_events():
    inotify = INotify()
    # TODO: add/remove flags to watch
    watch_flags = flags.CREATE | flags.DELETE | flags.MODIFY | flags.DELETE_SELF | flags.CLOSE_NOWRITE | flags.CLOSE_WRITE
    # add watch on file
    inotify.add_watch('/app/emba/log_1/emba.log', watch_flags)
    return inotify.read()
