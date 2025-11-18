# pylint: disable=R1732, C0201, E1129, W1509
__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021-2025 The AMOS Projects'
__author__ = 'Benedikt Kuehne, m-1-k-3, ClProsser, Luka Dekanozishvili'
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
from django.core.mail import send_mail
from django.template.loader import render_to_string

from uploader import finish_execution
from uploader.archiver import Archiver
from uploader.models import FirmwareAnalysis
from uploader.settings import get_emba_base_cmd
from embark.helper import get_size, zip_check
from porter.models import LogZipFile
from porter.importer import result_read_in
from users.models import User

logger = logging.getLogger(__name__)

# maximum concurrent running workers
MAX_WORKERS = 4
# maximum queue bound
MAX_QUEUE = MAX_WORKERS

# assign the threadpool max_worker_threads
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
# create semaphore to track queue state
semaphore = BoundedSemaphore(MAX_QUEUE)


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
                # write into pid file
                with open(f"{settings.EMBA_LOG_ROOT}/{analysis_id}/emba_run.pid", "w+", encoding="utf-8") as pid_file:
                    pid_file.write(str(proc.pid))
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
            sbom_log_location = f"{settings.EMBA_LOG_ROOT}/{analysis_id}/emba_logs/SBOM/EMBA_cyclonedx_sbom.json"
            error_log_location = f"{settings.EMBA_LOG_ROOT}/{analysis_id}/emba_logs/emba_error.log"

            # read f50_aggregator and store it into a Result form
            logger.info('Reading report from: %s', csv_log_location)
            logger.debug("contents of that dir are %r", Path(csv_log_location).exists())
            # if Path(csv_log_location).exists:
            if Path(csv_log_location).is_file() or Path(sbom_log_location).is_file():
                cls.csv_read(analysis_id=analysis_id, _path=csv_log_location, _cmd=cmd)
            elif Path(error_log_location).is_file():
                logger.error("No importable log file %s for report: %s generated", csv_log_location, analysis_id)
                logger.error("EMBA run was not successful!")
                exit_fail = True
            else:
                logger.error("EMBA run was probably not successful!")
                logger.error("Please check this manually and create a bug report!!")

            # take care of cleanup
            if active_analyzer_dir:
                shutil.rmtree(active_analyzer_dir)

        except builtins.Exception as exce:
            # fail
            logger.error("EMBA run was probably not successful!")
            logger.error("run_emba_cmd error: %s", exce)
            exit_fail = True
            logger.debug("sending email to admin")
            admin_email = User.objects.get(name="admin").email
            send_mail(subject="Failed EMBA run", message=f"analysis {analysis_id} failed @{timezone.now()}", from_email='system@' + settings.DOMAIN, recipient_list=[admin_email])

        # finalize db entry
        if analysis:
            analysis.end_date = timezone.now()
            analysis.scan_time = timezone.now() - analysis.start_date
            analysis.duration = str(analysis.scan_time)
            analysis.finished = True
            analysis.failed = exit_fail
            analysis.save(update_fields=["end_date", "scan_time", "duration", "finished", "failed"])

        if settings.EMAIL_ACTIVE is True:
            logger.debug("SEnding email with result")
            user = analysis.user
            mail_subject = 'Analysis completed'
            domain = settings.DOMAIN
            if exit_fail:
                message = render_to_string('uploader/email_run_failed.html', context={
                    'username': user.username,
                    'domain': domain,
                    'analysis_id': analysis_id
                })
            else:
                message = render_to_string('uploader/email_run_success.html', context={
                    'username': user.username,
                    'domain': domain,
                    'analysis_id': analysis_id
                })
            send_mail(mail_subject, message, 'system@' + settings.DOMAIN, [user.email])

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
            raise BoundedException("Killing EMBA process might have failed") from exce

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
        except builtins.Exception as exce:
            logger.error("Executor task could not be submitted")
            semaphore.release()
            raise exce
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
        analysis.status['last_phase'] = "Started zipping"
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
                    # 2.extract blindly
                    logger.debug("extracting....")
                    zip_.extractall(path=Path(f"{settings.EMBA_LOG_ROOT}/{analysis_id}/"))
                    logger.debug("finished unzipping....")
                else:
                    logger.info("There are inconsistencies with the zip file, extracting.....")
                    zip_.extractall(path=Path(f"{settings.EMBA_LOG_ROOT}/{analysis_id}/tmp/"))
                    logger.debug("finished unzipping, now renaming")
                    # renaming and moving
                    # 1. find toplevel in tmp (takes first find)
                    for root, dirs, _ in os.walk(Path(f"{settings.EMBA_LOG_ROOT}/{analysis_id}/tmp/")):
                        if os.path.dirname(dirs) == "html-report":
                            top_level = os.path.abspath(root)
                            break
                    # 2. move dirs and file from there into emba_logs
                    shutil.move(top_level, f"{settings.EMBA_LOG_ROOT}/{analysis_id}/emba_logs")
                # 3. sanity check (conformity)
                # TODO check the files
        except Exception as exce:
            logger.error("Unzipping failed: %s", exce)

        result_obj = result_read_in(analysis_id)
        if result_obj is None:
            logger.error("Readin failed.")
            return

        logger.debug("Got %s from zip", result_obj)

        analysis.end_date = timezone.now()
        analysis.scan_time = timezone.now() - analysis.start_date
        analysis.duration = str(analysis.scan_time)
        analysis.finished = True
        analysis.log_size = get_size(f"{settings.EMBA_LOG_ROOT}/{analysis_id}/emba_logs/")
        analysis.save(update_fields=["log_size", "end_date", "scan_time", "duration", "finished"])

    @classmethod
    def emba_check(cls, option):
        """
        does a emba dep check with option(int)

        1. run dep check with option
        2. return result via WS message
        Args:
            option 1/2
        """
        logger.debug("Checking EMBA with: %s", option)
        try:
            cmd = f"cd {settings.EMBA_ROOT} && {get_emba_base_cmd()} -d{option}"

            with open(f"{settings.EMBA_LOG_ROOT}/emba_update.log", "w+", encoding="utf-8") as file:
                proc = Popen(cmd, stdin=PIPE, stdout=file, stderr=file, shell=True)   # nosec
                # wait for completion
                proc.communicate()
                return_code = proc.wait()
            # success
            logger.info("Check Successful: %s", cmd)
            if return_code != 0:
                raise BoundedException("EMBA has non zero exit-code")
        except (BaseException, BoundedException) as exce:
            logger.error("emba dep check error: %s", exce)

        room_group_name = "versions"
        channel_layer = get_channel_layer()
        # send ws message
        async_to_sync(channel_layer.group_send)(
            room_group_name, {
                "type": 'send.message',
                "message": {f"EMBA dep check {option}": return_code}
            }
        )

    @classmethod
    def emba_update(cls, option):
        """
        does a emba update with either git or source

        1. Update state of original emba dir (not the servers) - git checkout origin/master
        2. re-install emba through script + docker pull
        Args:
            option GIT / DOCKER / NVD

        """
        logger.debug("Update EMBA with: %s", option)
        # update using diffrent methods
        if os.environ.get('EMBA_INSTALL') != "no":
            # git update
           if os.path.exists(os.path.join(settings.EMBA_ROOT),'.git'):
                try:
                    cmd = f"cd {settings.EMBA_ROOT} && git pull origin master"

                    with open(f"{settings.EMBA_LOG_ROOT}/emba_update.log", "w+", encoding="utf-8") as file:
                        proc = Popen(cmd, stdin=PIPE, stdout=file, stderr=file, shell=True)   # nosec
                        # wait for completion
                        proc.communicate()
                        return_code = proc.wait()
                    # success
                    logger.info("Git pull Successful: %s", cmd)
                    if return_code != 0:
                        raise BoundedException("Git has non zero exit-code")
                except (BaseException, BoundedException) as exce:
                    logger.error("emba update error: %s", exce)
        # src
        else:
            # rm emba
            # call installer.sh -e
            # TODO
            pass
        room_group_name = "versions"
        channel_layer = get_channel_layer()
        # send ws message
        async_to_sync(channel_layer.group_send)(
            room_group_name, {
                "type": 'send.message',
                "message": {f"EMBA update {option}": return_code}
            }
        )

    @classmethod
    def emba_upgrade(cls):
        """
        Reinstalls dependency
        
        # 1. Update state of original emba dir (not the servers)
        # 2. remove external dir
        # 3. re-install emba through script + docker pull
        # 4. sync server dir
        """
        # TODO missing docker and NVD
        # TODO best way to upgrade EMBA?
        # emba upgrade
        try:
            cmd = f"cd {settings.EMBA_ROOT} && {get_emba_base_cmd()} -U"

            with open(f"{settings.EMBA_LOG_ROOT}/emba_update.log", "a", encoding="utf-8") as file:
                proc = Popen(cmd, stdin=PIPE, stdout=file, stderr=file, shell=True)   # nosec
                # wait for completion
                proc.communicate()
                return_code = proc.wait()
            # success
            logger.info("EMBA update Successful: %s", cmd)
            if return_code != 0:
                raise BoundedException("EMBA has non zero exit-code")
        except (BaseException, BoundedException) as exce:
            logger.error("emba update error: %s", exce)

        room_group_name = "versions"
        channel_layer = get_channel_layer()
        # send ws message
        async_to_sync(channel_layer.group_send)(
            room_group_name, {
                "type": 'send.message',
                "message": {f"EMBA upgrade ": return_code}
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

    @classmethod
    def submit_emba_update(cls, option):
        # submit update to executor threadpool
        emba_fut = BoundedExecutor.submit(cls.emba_update, option)
        return emba_fut

    @classmethod
    def submit_emba_upgrade(cls, option):
        # submit upgrade to executor threadpool
        emba_fut = BoundedExecutor.submit(cls.emba_upgrade, option)
        return emba_fut

    @staticmethod
    @receiver(finish_execution, sender='system')
    def sigint_handler(sender, **kwargs):
        logger.info("Received shutdown signal  by %s", sender)
        BoundedExecutor.shutdown()
