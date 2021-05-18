import logging
import subprocess
from concurrent.futures.thread import ThreadPoolExecutor
from subprocess import Popen
from threading import BoundedSemaphore

from django.conf import settings


class boundedExecutor:
    """
        class boundedExecutor
        This class is a wrapper of ExecuterThreadPool to enable a limited queue
        Used to handle concurrent emba analysis as well as emba.log analyzer
    """

    def __init__(self, bound, max_workers):

        # assign the threadpool max_worker_threads
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        # create semaphore to track queue state
        self.semaphore = BoundedSemaphore(bound + max_workers)

        # emba directories
        self.emba_script_location = "/app/emba/emba.sh"
        self.emba_log_location = "/app/emba/log_{}"

    """
        run shell commands from python script as subprocess, waits for termination and evaluates returncode

        :param cmd: shell command to be executed

        :return:
    """

    def run_shell_cmd(self, cmd):

        logging.info(cmd)

        # get return code to evaluate: 0 = success, 1 = failure,
        # see emba.sh for further information
        try:
            # run emba_process and wait for completion

            # TODO emba.log need to be informed
            emba_process = subprocess.run(cmd, shell=True, check=True)

            # success
            logging.info("cmd run successful")
            logging.info(emba_process.returncode)
            # TODO: inform asgi to propagate success to frontend

        except Exception as ex:
            logging.error("{0}".format(ex))
            # TODO: inform asgi to propagate error to frontend

    """
        run_shell_cmd but elevated

        :param cmd: shell command to be executed elevated

        :return:
    """

    def run_shell_cmd_elavated(self, cmd):
        self.run_shell_cmd("sudo" + cmd)

    """
        submit firmware + metadata for emba execution

        params: firmware object (TODO)

        return: emba process future on success, None on failure
    """

    def submit_firmware(self, firmware):

        # TODO extract information from parameter / define proper interface
        image_file_name = "/DIR300B5_FW214WWB01.bin"
        # image_file_location = settings.MEDIA_ROOT + image_file_name
        image_file_location = "/app/firmware" + image_file_name

        # evaluate meta information
        real_emba_log_location = self.emba_log_location.format("1")
        emba_flags = "-t -g -s -z -W -F"

        # build command
        emba_cmd = "{0} -f {1} -l {2} {3}".format(self.emba_script_location, image_file_location,
                                                  real_emba_log_location, emba_flags)

        # submit command to executor threadpool
        emba_fut = self.executor.submit(self.run_shell_cmd, emba_cmd)

        return emba_fut

    """
        same as concurrent.futures.Executor#submit, but with queue

        params: see concurrent.futures.Executor#submit

        return: future on success, None on full queue
    """

    def submit(self, fn, *args, **kwargs):

        # check if semaphore can be acquired, if not queue is full
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
