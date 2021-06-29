import logging
import os
import shutil
import subprocess

from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from threading import BoundedSemaphore

from django.utils.datetime_safe import datetime
from django.conf import settings

from .archiver import Archiver
from .models import Firmware
from embark.logreader import LogReader

logger = logging.getLogger('web')

# maximum concurrent running workers
max_workers = 4
# maximum queue bound
max_queue = 0

# assign the threadpool max_worker_threads
executor = ThreadPoolExecutor(max_workers=max_workers)
# create semaphore to track queue state
semaphore = BoundedSemaphore(max_queue + max_workers)

# emba directories
emba_script_location = "/app/emba/emba.sh"


class BoundedExecutor:
    """
    class BoundedExecutor
    This class is a wrapper of ExecuterThreadPool to enable a limited queue
    Used to handle concurrent emba analysis as well as emba.log analyzer
    """

    @classmethod
    def run_emba_cmd(cls, cmd, primary_key=None, active_analyzer_dir=None):
        """
        run shell commands from python script as subprocess, waits for termination and evaluates returncode

        :param cmd: shell command to be executed
        :param primary_key: primary key for firmware entry db identification
        :param active_analyzer_dir: active analyzer dir for deletion afterwards

        :return:
        """

        logger.info(f"Starting: {cmd}")

        # get return code to evaluate: 0 = success, 1 = failure,
        # see emba.sh for further information
        try:

            # run emba_process and wait for completion
            emba_process = subprocess.call(cmd, shell=True)

            # success
            logger.info(f"Success: {cmd}")

            # take care of cleanup
            if active_analyzer_dir:
                shutil.rmtree(active_analyzer_dir)

        except Exception as ex:
            # fail
            logger.error(f"{ex}")

            # finalize db entry
            if primary_key:
                firmware = Firmware.objects.get(pk=primary_key)
                firmware.end_date = datetime.now()
                firmware.failed = True
                firmware.save()

        else:
            # finalize db entry
            if primary_key:
                firmware = Firmware.objects.get(pk=primary_key)
                firmware.end_date = datetime.now()
                firmware.finished = True
                firmware.save()

            logger.info(f"Successful cleaned up: {cmd}")

        finally:
            # take care of cleanup
            if active_analyzer_dir:
                shutil.rmtree(active_analyzer_dir)

    @classmethod
    def run_emba_cmd_elavated(cls, cmd, primary_key, active_analyzer_dir):
        """
        run_shell_cmd but elevated

        param cmd: shell command to be executed elevated
        param primary_key: primary key for firmware entry db identification
        param active_analyzer_dir: active analyzer dir for deletion afterwards

        :return:
        """

        cls.run_emba_cmd(f"sudo {cmd}", primary_key, active_analyzer_dir)

    @classmethod
    def submit_firmware(cls, firmware_flags, firmware_file):
        """
        submit firmware + metadata for emba execution

        params firmware_flags: firmware model with flags and metadata
        params firmware_file: firmware file model to be analyzed

        return: emba process future on success, None on failure
        """

        # unpack firmware file to </app/embark/uploadedFirmwareImages/active_{ID}/>
        active_analyzer_dir = f"/app/embark/{settings.MEDIA_ROOT}/active_{firmware_flags.id}/"

        if firmware_file.is_archive:
            Archiver.unpack(firmware_file.file.path, active_analyzer_dir)
            # TODO: maybe descent in directory structure
        else:
            Archiver.copy(firmware_file.file.path, active_analyzer_dir)

        # find emba start_file
        emba_startfile = os.listdir(active_analyzer_dir)
        if len(emba_startfile) == 1:
            image_file_location = f"{active_analyzer_dir}{emba_startfile.pop()}"
            logger.error(f"{image_file_location}")
        else:
            logger.error(f"Uploaded file: {firmware_file} doesnt comply with processable files.\n zip folder with no "
                         f"extra directory in between.")
            shutil.rmtree(active_analyzer_dir)
            return None

        # get emba flags from command parser
        emba_flags = firmware_flags.get_flags()

        # evaluate meta information and safely create log dir
        emba_log_location = f"/app/emba/{settings.LOG_ROOT}/{firmware_flags.pk}"

        firmware_flags.path_to_logs = emba_log_location
        firmware_flags.save()

        # build command
        emba_cmd = f"{emba_script_location} -f {image_file_location} -l {emba_log_location} {emba_flags}"

        # submit command to executor threadpool
        emba_fut = BoundedExecutor.submit(cls.run_emba_cmd, emba_cmd, firmware_flags.pk, active_analyzer_dir)

        # start log_reader TODO: cancel future and return future
        log_read_fut = BoundedExecutor.submit(LogReader, firmware_flags.pk)

        return emba_fut

    @classmethod
    def submit(cls, fn, *args, **kwargs):
        """
        same as concurrent.futures.Executor#submit, but with queue

        params: see concurrent.futures.Executor#submit

        return: future on success, None on full queue
        """

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

    @classmethod
    def shutdown(cls, wait=True):
        """See concurrent.futures.Executor#shutdown"""

        executor.shutdown(wait)
