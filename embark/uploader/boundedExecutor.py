import logging
import shutil
import subprocess
from concurrent.futures.thread import ThreadPoolExecutor
from threading import BoundedSemaphore

from django.conf import settings

from uploader import archiver


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

            # TODO: progress bar needs to be started
            emba_process = subprocess.call(cmd, shell=True)

            # success
            logging.info("Success: {0}".format(cmd))
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

    def submit_firmware(self, firmware_flags, firmware_file):

        # unpack firmware file to </app/embark/uploadedFirmwareImages/active_{ID}/>
        active_analyzer_dir = "/app/embark/{0}/active_{1}/".format(settings.MEDIA_ROOT, firmware_flags.id)
        archiver.unpack(firmware_file.file.path, active_analyzer_dir)

        # get emba flags from command parser
        emba_flags = firmware_flags.get_flags()

        # TODO: Maybe check if file or dir
        image_file_location = "{0}*".format(active_analyzer_dir)

        # evaluate meta information
        emba_log_location = "/app/embark/{0}/active_{1}/".format(settings.LOG_ROOT, firmware_flags.id)

        # build command
        emba_cmd = "{0} -f {1} -l {2} {3}".format(self.emba_script_location, image_file_location,
                                                  emba_log_location, emba_flags)

        # submit command to executor threadpool
        emba_fut = self.executor.submit(self.run_shell_cmd, emba_cmd)
        # take care of cleanup
        emba_fut.add_done_callback(lambda x: shutil.rmtree(active_analyzer_dir))

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
