import rx
from rx import Observable
import rx.operators as ops
import re

lines = []


def process_line(inp, pat):
    if re.match(pat, inp):
        return True
    else:
        return False


# function for opening log file
def input_processing():
    return "uuuh mamam"
    # pattern = "\[\*\]*"
    # with open('/app/emba/logs/emba.log') as f:
    #     source_stream = rx.from_(f)
    #
    #     return source_stream.pipe(
    #         ops.filter(lambda s: process_line(s, pattern)),
    #         ops.flat_map(lambda a: a.split("-"))
    #     )
