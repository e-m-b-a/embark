# pylint: disable=R1732, C0201, E1129, W1509
__copyright__ = 'Copyright 2021-2024 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'Benedikt Kuehne, m-1-k-3'
__license__ = 'MIT'

import builtins
import logging
import os
import shutil
from subprocess import Popen, PIPE
import zipfile

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from django.db import close_old_connections

from uploader import finish_execution
from uploader.archiver import Archiver
from uploader.models import FirmwareAnalysis
from embark.logreader import LogReader
from embark.helper import get_size, zip_check
from porter.models import LogZipFile
from porter.importer import result_read_in


logger = logging.getLogger(__name__)

# maximum concurrent running workers
MAX_WORKERS = 4
# maximum queue bound
MAX_QUEUE = MAX_WORKERS

# assign the threadpool max_worker_threads
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
# create semaphore to track queue state
semaphore = BoundedSemaphore(MAX_QUEUE)

# emba directories
EMBA_SCRIPT_LOCATION = f"cd {settings.EMBA_ROOT} && sudo ./emba"


class BoundedException(Exception):
    pass


class BoundedExecutor:
    """
    class BoundedExecutor
    This class is a wrapper of ExecuterThreadPool to enable a limited queue
    Used to handle concurrent emba analysis as well as emba.log analyzer
    """

    @classmethod
    def run_emba_cmd(cls, cmd, analysis_id=None, active_analyzer_dir=None):
        """
        run shell commands from python script as subprocess, waits for termination and evaluates returncode

        :param cmd: shell command to be executed
        :param id: primary key for firmware entry db identification
        :param active_analyzer_dir: active analyzer dir for deletion afterwards

        :return:
        """

        logger.info("Starting: %s", cmd)

        # get return code to evaluate: 0 = success, 1 = failure,
        # see emba for further information
        exit_fail = False
        try:

            analysis = FirmwareAnalysis.objects.get(id=analysis_id)
            return_code = 0

            # The os.setsid() is passed in the argument preexec_fn so it's run after the fork() and before  exec() to run the shell.
            # attached but synchronous
            with open(f"{settings.EMBA_LOG_ROOT}/{analysis_id}/emba_run.log", "w+", encoding="utf-8") as file:
                proc = Popen(cmd, stdin=PIPE, stdout=file, stderr=file, shell=True, start_new_session=True)   # nosec
                # Add proc to FirmwareAnalysis-Object
                analysis.pid = proc.pid
                analysis.save(update_fields=["pid"])
                logger.debug("subprocess got pid %s", proc.pid)
                # wait for completion
                proc.communicate()
                return_code = proc.wait()

            # success
            logger.info("Success: %s", cmd)
            logger.info("EMBA returned: %d", return_code)
            if return_code != 0:
                raise BoundedException("EMBA has non zero exit-code")

            close_old_connections()
            # get csv log location
            csv_log_location = f"{settings.EMBA_LOG_ROOT}/{analysis_id}/emba_logs/csv_logs/f50_base_aggregator.csv"

            # read f50_aggregator and store it into a Result form
            logger.info('Reading report from: %s', csv_log_location)
            logger.debug("contents of that dir are %r", Path(csv_log_location).exists())
            # if Path(csv_log_location).exists:
            if Path(csv_log_location).is_file():
                cls.csv_read(analysis_id=analysis_id, _path=csv_log_location, _cmd=cmd)
            else:
                logger.error("CSV file %s for report: %s not generated", csv_log_location, analysis_id)
                logger.error("EMBA run was probably not successful!")
                exit_fail = True

            # take care of cleanup
            if active_analyzer_dir:
                shutil.rmtree(active_analyzer_dir)

        except builtins.Exception as execpt:
            # fail
            logger.error("EMBA run was probably not successful!")
            logger.error("run_emba_cmd error: %s", execpt)
            exit_fail = True

        # finalize db entry
        if analysis:
            analysis.end_date = timezone.now()
            analysis.scan_time = timezone.now() - analysis.start_date
            analysis.duration = str(analysis.scan_time)
            analysis.finished = True
            analysis.failed = exit_fail
            analysis.save(update_fields=["end_date", "scan_time", "duration", "finished", "failed"])

        logger.info("Successful cleaned up: %s", cmd)

    @classmethod
    def kill_emba_cmd(cls, analysis_id):
        """
        run shell commands from python script as subprocess, waits for termination and evaluates returncode

        :param analysis_id: primary key for firmware-analysis entry
        :param active_analyzer_dir: active analyzer dir for deletion afterwards

        :return:
        """
        logger.info("Killing ID: %s", analysis_id)
        try:
            # logger.debug("%s", id)
            cmd = f"sudo pkill -f {analysis_id}"
            with open(f"{settings.EMBA_LOG_ROOT}/{analysis_id}_kill.log", "w+", encoding="utf-8") as file:
                proc = Popen(cmd, stdin=PIPE, stdout=file, stderr=file, shell=True)   # nosec
                # wait for completion
                proc.communicate()
            # success
            logger.info("Kill Successful: %s", cmd)
        except BaseException as exce:
            logger.error("kill_emba_cmd error: %s", exce)

    @classmethod
    def submit_kill(cls, uuid):
        # submit command to executor threadpool
        emba_fut = BoundedExecutor.submit(cls.kill_emba_cmd, uuid)
        analysis = FirmwareAnalysis.objects.get(id=uuid)
        analysis.status['finished'] = True
        analysis.failed = True
        analysis.finished = True
        analysis.save(update_fields=["status", "finished", "failed"])
        return emba_fut

    @classmethod
    def submit_firmware(cls, firmware_flags, firmware_file):
        """
        submit firmware + metadata for emba execution

        params firmware_flags: firmware model with flags and metadata
        params firmware_file: firmware file model to be analyzed

        return: emba process future on success, None on failure
        """
        active_analyzer_dir = f"{settings.ACTIVE_FW}/{firmware_flags.id}/"
        logger.info("submitting firmware %s to emba", active_analyzer_dir)

        Archiver.copy(src=firmware_file.file.path, dst=active_analyzer_dir)

        # copy success
        emba_startfile = os.listdir(active_analyzer_dir)
        logger.debug("active dir contents %s", emba_startfile)
        if len(emba_startfile) == 1:
            image_file_location = f"{active_analyzer_dir}{emba_startfile.pop()}"
        else:
            logger.error("Uploaded file: %s doesnt comply with processable files.", firmware_file)
            logger.error("Zip folder with no extra directory in between.")
            shutil.rmtree(active_analyzer_dir)
            return None

        # get emba flags from command parser
        emba_flags = firmware_flags.get_flags()

        # evaluate meta information and safely create log dir

        emba_log_location = f"{settings.EMBA_LOG_ROOT}/{firmware_flags.id}/emba_logs"
        log_path = Path(emba_log_location).parent
        log_path.mkdir(parents=True, exist_ok=True)

        firmware_flags.path_to_logs = emba_log_location
        firmware_flags.status["analysis"] = str(firmware_flags.id)
        firmware_flags.status["firmware_name"] = firmware_flags.firmware_name
        firmware_flags.save(update_fields=["status", "path_to_logs"])

        emba_cmd = f"{EMBA_SCRIPT_LOCATION} -p ./scan-profiles/default-scan-no-notify.emba -f {image_file_location} -l {emba_log_location} {emba_flags}"

        # submit command to executor threadpool
        emba_fut = BoundedExecutor.submit(cls.run_emba_cmd, emba_cmd, firmware_flags.id, active_analyzer_dir)

        # start log_reader TODO: cancel future and return future
        # log_read_fut = BoundedExecutor.submit(LogReader, firmware_flags.pk)
        BoundedExecutor.submit(LogReader, firmware_flags.id)

        return emba_fut

    @classmethod
    def submit(cls, function_cmd, *args, **kwargs):
        """
        same as concurrent.futures.Executor#submit, but with queue

        params: see concurrent.futures.Executor#submit

        return: future on success, None on full queue
        """

        logger.info("submit fn: %s", function_cmd)
        logger.info("submit cls: %s", cls)

        # check if semaphore can be acquired, if not queue is full
        queue_not_full = semaphore.acquire(blocking=False)
        if not queue_not_full:
            logger.error("Executor queue full")
            return None
        try:
            future = executor.submit(function_cmd, *args, **kwargs)
        except builtins.Exception as error:
            logger.error("Executor task could not be submitted")
            semaphore.release()
            raise error
        future.add_done_callback(lambda x: semaphore.release())
        return future

    @classmethod
    def shutdown(cls, wait=True):
        """See concurrent.futures.Executor#shutdown"""
        logger.info("shutting down Boundedexecutor")
        executor.shutdown(wait)
        # set all running analysis to failed
        running_analysis_list = FirmwareAnalysis.objects.filter(finished=False).exclude(failed=True)
        for analysis_ in running_analysis_list:
            analysis_.failed = True
            analysis_.finished = True
            analysis_.save(update_fields=["finished", "failed"])
        logger.info("Shutdown successful")

    @classmethod
    def csv_read(cls, analysis_id, _path, _cmd):
        """
        This job reads the F50_aggregator file and stores its content into the Result model
        """
        return result_read_in(analysis_id=analysis_id)

    @classmethod
    def zip_log(cls, analysis_id):
        """
        Zipps the logs produced by emba
        :param analysis_id: primary key for firmware-analysis entry
        """
        logger.debug("Zipping ID: %s", analysis_id)
        analysis = FirmwareAnalysis.objects.get(id=analysis_id)
        analysis.finished = False
        analysis.status['finished'] = False
        analysis.status['work'] = True
        analysis.status['last_update'] = str(timezone.now())
        analysis.status['last_phase'] = "Started Zipping"
        analysis.save()

        room_group_name = f"services_{analysis.user}"
        channel_layer = get_channel_layer()
        # send ws message
        async_to_sync(channel_layer.group_send)(
            room_group_name, {
                "type": 'send.message',
                "message": {str(analysis.id): analysis.status}
            }
        )
        try:
            # archive = Archiver.pack(f"{settings.MEDIA_ROOT}/log_zip/{analysis_id}", 'zip', analysis.path_to_logs, './*')
            archive = Archiver.make_zipfile(f"{settings.MEDIA_ROOT}/log_zip/{analysis_id}.zip", analysis.path_to_logs)

            # create a LogZipFile obj
            analysis.zip_file = LogZipFile.objects.create(file=archive, user=analysis.user)
        except builtins.Exception as exce:
            logger.error("Zipping failed: %s", exce)
        analysis.finished = True
        analysis.status['finished'] = True
        analysis.status['work'] = False
        analysis.status['last_update'] = str(timezone.now())
        analysis.status['last_phase'] = "Finished Zipping"
        analysis.save()
        # send ws message
        async_to_sync(channel_layer.group_send)(
            room_group_name, {
                "type": 'send.message',
                "message": {str(analysis.id): analysis.status}
            }
        )

    @classmethod
    def unzip_log(cls, analysis_id, file_loc):
        """
        unzipps the logs
        1. copy into settings.EMBA_LOG_ROOT with id
        2. read csv into result result_model
        Args:
            current location
            object with needed pk
        """
        logger.debug("Zipping ID: %s", analysis_id)
        analysis = FirmwareAnalysis.objects.get(id=analysis_id)
        analysis.finished = False
        analysis.save(update_fields=["finished"])
        try:
            with zipfile.ZipFile(file_loc, 'r') as zip_:
                # 1.check archive contents (security)
                zip_contents = zip_.namelist()
                if zip_check(zip_contents):
                    # 2.extract
                    logger.debug("extracting....")
                    zip_.extractall(path=Path(f"{settings.EMBA_LOG_ROOT}/{analysis_id}/"))
                    logger.debug("finished unzipping....")
                else:
                    logger.error("Wont extract since there are inconsistencies with the zip file")

                # 3. sanity check (conformity)
                # TODO check the files
        except builtins.Exception as exce:
            logger.error("Unzipping failed: %s", exce)

        result_obj = result_read_in(analysis_id)
        if result_obj is None:
            logger.error("Readin failed: %s", exce)
            return

        logger.debug("Got %s from zip", result_obj)

        analysis.finished = True
        analysis.log_size = get_size(f"{settings.EMBA_LOG_ROOT}/{analysis_id}/emba_logs/")
        analysis.save(update_fields=["finished", "log_size"])

    @classmethod
    def emba_check(cls, option):
        """
        does a emba dep check with option(int)

        1. run dep check with option
        2. return result via WS message
        Args:
            option 1/2
        """
        logger.debug("Checking EMBA with: %d", option)
        try:
            cmd = f"{EMBA_SCRIPT_LOCATION} -d{option}"

            with open(f"{settings.EMBA_LOG_ROOT}/check.log", "w+", encoding="utf-8") as file:
                proc = Popen(cmd, stdin=PIPE, stdout=file, stderr=file, shell=True)   # nosec
                # wait for completion
                proc.communicate()
            # success
            logger.info("Check Successful: %s", cmd)
        except BaseException as exce:
            logger.error("emba dep check error: %s", exce)
        
        # TODO take resulting log and show to user
            
        room_group_name = f"versions"
        channel_layer = get_channel_layer()
        # send ws message
        async_to_sync(channel_layer.group_send)(
            room_group_name, {
                "type": 'send.message',
                "message": {}   # TODO same as logviewer
            }
        )
        

    @classmethod
    def submit_zip(cls, uuid):
        # submit zip req to executor threadpool
        emba_fut = BoundedExecutor.submit(cls.zip_log, uuid)
        return emba_fut

    @classmethod
    def submit_unzip(cls, uuid, file_loc):
        # submit zip req to executor threadpool
        emba_fut = BoundedExecutor.submit(cls.unzip_log, uuid, file_loc)
        return emba_fut

    @classmethod
    def submit_emba_check(cls, option):
        # submit dep check to executor threadpool
        emba_fut = BoundedExecutor.submit(cls.emba_check, option)
        return emba_fut

    @staticmethod
    @receiver(finish_execution, sender='system')
    def sigint_handler(sender, **kwargs):
        logger.info("Received shutdown signal  by %s", sender)
        BoundedExecutor.shutdown()
