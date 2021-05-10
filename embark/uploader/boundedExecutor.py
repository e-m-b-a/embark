import logging
from concurrent.futures.thread import ThreadPoolExecutor
from subprocess import Popen
from threading import BoundedSemaphore


class boundedExecutor:
    def __init__(self, bound, max_workers):

        # assign the threadpool max_worker_threads
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        # create semaphore to track queue state
        self.semaphore = BoundedSemaphore(bound + max_workers)

        # emba directories
        self.emba_script_location = "/app/emba/emba.sh"
        self.emba_log_location = "/app/emba/log_%s"

    def run_shell_cmd(self, cmd):

        # TODO emba.log analyzer needs to be started
        emba_process = Popen(cmd, shell=True)
        emba_process.wait()

        if emba_process.returncode == 0:
            # display help
            print("display help")
            pass
        elif emba_process.returncode == 1:
            # error occured consult log
            print("error occured consult log")
            pass
        else:
            # dunno
            print("dunno")
            pass

    def submit_firmware(self, firmware):

        # TODO extract information from parameter
        image_file_location = 0
        image_file_name = "img"
        log_file_location = 0

        real_emba_log_location = (self.emba_log_location, image_file_name)
        emba_flags = "-D -i -g -s -z -W"

        emba_cmd = ("%s -f %s -l %s %s", real_emba_log_location, image_file_location, log_file_location, emba_flags)

        emba_fut = self.executor.submit(self.run_shell_cmd, emba_cmd)

        if not emba_fut:
            # TODO handle full queue
            pass

        return emba_fut

    """See concurrent.futures.Executor#submit"""

    def submit(self, fn, *args, **kwargs):

        queue_not_full = self.semaphore.acquire(blocking=False)
        if not queue_not_full:
            logging.error("Executor queue full")
            return None

        try:
            future = self.executor.submit(fn, *args, **kwargs)
        except Exception as e:
            logging.error("Executor task could not be submitted")
            self.semaphore.release()
            raise e
        else:
            future.add_done_callback(lambda x: self.semaphore.release())
            return future

    """See concurrent.futures.Executor#shutdown"""

    def shutdown(self, wait=True):
        self.executor.shutdown(wait)
