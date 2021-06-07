import logging
import shutil
import subprocess
from concurrent.futures.thread import ThreadPoolExecutor
from threading import BoundedSemaphore

from django.utils.datetime_safe import datetime
from django.conf import settings

from .archiver import Archiver
from .models import Firmware

logger = logging.getLogger('web')

max_workers = 2
max_queue = 2

# assign the threadpool max_worker_threads
executor = ThreadPoolExecutor(max_workers=max_workers)
# create semaphore to track queue state
semaphore = BoundedSemaphore(max_queue + max_workers)

# emba directories
emba_script_location = "/app/emba/emba.sh"


"""
    class BoundedExecutor
    This class is a wrapper of ExecuterThreadPool to enable a limited queue
    Used to handle concurrent emba analysis as well as emba.log analyzer
"""


class BoundedExecutor:
    """
        run shell commands from python script as subprocess, waits for termination and evaluates returncode

        :param cmd: shell command to be executed

        :return:
    """
    @classmethod
    def run_emba_cmd(cls, cmd, primary_key=None, active_analyzer_dir=None):

        logger.info(f"Starting: {cmd}")

        # get return code to evaluate: 0 = success, 1 = failure,
        # see emba.sh for further information
        try:
            # run emba_process and wait for completion

            # TODO: progress bar needs to be started
            emba_process = subprocess.call(cmd, shell=True)

            # success
            logger.info(f"Success: {cmd}")

            # take care of cleanup
            if active_analyzer_dir:
                shutil.rmtree(active_analyzer_dir)

            # finalize db entry
            if primary_key:
                firmware = Firmware.objects.get(pk=primary_key)
                firmware.end_date = datetime.now()
                firmware.finished = True
                firmware.save()

            # success
            logger.info(f"Successful cleaned up: {cmd}")

        except Exception as ex:
            logger.error(f"{ex}")

            # take care of cleanup
            if active_analyzer_dir:
                shutil.rmtree(active_analyzer_dir)

            # finalize db entry
            if primary_key:
                firmware = Firmware.objects.get(pk=primary_key)
                firmware.end_date = datetime.now()
                firmware.failed = True
                firmware.save()

    """
        run_shell_cmd but elevated

        :param cmd: shell command to be executed elevated

        :return:
    """
    @classmethod
    def run_emba_cmd_elavated(cls, cmd, primary_key, active_analyzer_dir):
        cls.run_emba_cmd(f"sudo {cmd}", primary_key, active_analyzer_dir)

    """
        submit firmware + metadata for emba execution

        params: firmware object (TODO)

        return: emba process future on success, None on failure
    """
    @classmethod
    def submit_firmware(cls, firmware_flags, firmware_file):

        # unpack firmware file to </app/embark/uploadedFirmwareImages/active_{ID}/>
        active_analyzer_dir = f"/app/embark/{settings.MEDIA_ROOT}/active_{firmware_flags.id}/"
        Archiver.unpack(firmware_file.file.path, active_analyzer_dir)

        # get emba flags from command parser
        emba_flags = firmware_flags.get_flags()

        # TODO: Maybe check if file or dir
        image_file_location = f"{active_analyzer_dir}*"

        # evaluate meta information
        emba_log_location = f"/app/emba/{settings.LOG_ROOT}/"
        firmware_flags.path_to_logs = emba_log_location
        firmware_flags.save()

        # build command
        emba_cmd = f"{emba_script_location} -f {image_file_location} -l {emba_log_location} {emba_flags}"

        # submit command to executor threadpool
        emba_fut = executor.submit(cls.run_emba_cmd, emba_cmd, firmware_flags.pk, active_analyzer_dir)

        return emba_fut

    """
        same as concurrent.futures.Executor#submit, but with queue

        params: see concurrent.futures.Executor#submit

        return: future on success, None on full queue
    """
    @classmethod
    def submit(cls, fn, *args, **kwargs):

        # check if semaphore can be acquired, if not queue is full
        queue_not_full = semaphore.acquire(blocking=False)
        if not queue_not_full:
            logger.error(f"Executor queue full")
            return None

        try:
            future = executor.submit(fn, *args, **kwargs)
        except Exception as e:
            logger.error(f"Executor task could not be submitted")
            semaphore.release()
            raise e
        else:
            future.add_done_callback(lambda x: semaphore.release())
            return future

    """See concurrent.futures.Executor#shutdown"""
    @classmethod
    def shutdown(cls, wait=True):
        executor.shutdown(wait)
