# pylint: disable=R1732, C0201, E1129, W1509
import csv
import logging
import os
import shutil
from subprocess import Popen, PIPE
import re
import json

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore

from django.utils.datetime_safe import datetime
from django.conf import settings

from uploader.archiver import Archiver
from uploader.models import FirmwareAnalysis
from dashboard.models import Result
from embark.logreader import LogReader


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
                proc = Popen(cmd, stdin=PIPE, stdout=file, stderr=file, shell=True)   # nosec
                # Add proc to FirmwareAnalysis-Object
                analysis.pid = proc.pid
                analysis.save()
                logger.debug("subprocess got pid %s", proc.pid)
                # wait for completion
                proc.communicate()
                return_code = proc.wait()

            # success
            logger.info("Success: %s", cmd)
            logger.info("EMBA returned: %d", return_code)
            # if return_code != 0:
            #     raise Exception

            # get csv log location
            csv_log_location = f"{settings.EMBA_LOG_ROOT}/{analysis_id}/emba_logs/csv_logs/f50_base_aggregator.csv"

            # read f50_aggregator and store it into a Result form
            logger.info('Reading report from: %s', csv_log_location)
            logger.debug("contents of that dir are %r", Path(csv_log_location).exists())
            # if Path(csv_log_location).exists:
            if Path(csv_log_location).is_file():
                cls.csv_read(analysis_id=analysis_id, path=csv_log_location, cmd=cmd)
            else:
                logger.error("CSV file %s for report: %s not generated", csv_log_location, analysis_id)
                logger.error("EMBA run was probably not successful!")
                exit_fail = True

            # take care of cleanup
            if active_analyzer_dir:
                shutil.rmtree(active_analyzer_dir)

        except Exception as execpt:
            # fail
            logger.error("EMBA run was probably not successful!")
            logger.error("run_emba_cmd error: %s", execpt)
            exit_fail = True
        finally:
            # finalize db entry
            if analysis_id:
                analysis.end_date = datetime.now()
                analysis.scan_time = datetime.now() - analysis.start_date
                analysis.duration = str(analysis.scan_time)
                analysis.finished = True
                analysis.failed = exit_fail
                analysis.save()

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
        firmware_flags.save()

        # build command
        # FIXME remove all flags
        # TODO add note with uuid
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
        except Exception as error:
            logger.error("Executor task could not be submitted")
            semaphore.release()
            raise error
        else:
            future.add_done_callback(lambda x: semaphore.release())
            return future

    @classmethod
    def shutdown(cls, wait=True):
        """See concurrent.futures.Executor#shutdown"""

        executor.shutdown(wait)

    @classmethod
    def csv_read(cls, analysis_id, path, cmd):
        """
        This job reads the F50_aggregator file and stores its content into the Result model
        """

        res_dict = {}
        with open(path, newline='\n', encoding='utf-8') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=';')
            csv_list = []
            for _row in csv_reader:
                # remove NA
                if "NA" in _row:
                    _row.remove("NA")
                # remove empty
                if "" in _row:
                    _row.remove("")
                csv_list.append(_row)
                for _element in csv_list:
                    if _element[0] == "version_details":
                        res_dict[_element[1]] = _element[2:]
                    elif len(_element) == 2:
                        res_dict[_element[0]] = _element[1]
                    elif len(_element) == 3:
                        if not _element[0] in res_dict.keys():
                            res_dict[_element[0]] = {}
                        res_dict[_element[0]][_element[1]] = _element[2]
                    else:
                        pass

        logger.info("result dict: %s", res_dict)
        res_dict.pop('FW_path', None)

        entropy_value = res_dict.get("entropy_value", 0)
        # if type(entropy_value) is str:
        if isinstance(entropy_value, str):
            # entropy_value = re.findall(r'(\d+\.?\d*)', ' 7.55 bits per byte.')[0]
            entropy_value = re.findall(r'(\d+\.?\d*)', entropy_value)[0]
            entropy_value = entropy_value.strip('.')

        res = Result(
            firmware_analysis=FirmwareAnalysis.objects.get(id=analysis_id),
            emba_command=cmd.replace(f"cd {settings.EMBA_ROOT} && ", ""),
            architecture_verified=res_dict.get("architecture_verified", ''),
            # os_unverified=res_dict.get("os_unverified", ''),
            os_verified=res_dict.get("os_verified", ''),
            files=int(res_dict.get("files", 0)),
            directories=int(res_dict.get("directories", 0)),
            entropy_value=float(entropy_value),
            shell_scripts=int(res_dict.get("shell_scripts", 0)),
            shell_script_vulns=int(res_dict.get("shell_script_vulns", 0)),
            kernel_modules=int(res_dict.get("kernel_modules", 0)),
            kernel_modules_lic=int(res_dict.get("kernel_modules_lic", 0)),
            interesting_files=int(res_dict.get("interesting_files", 0)),
            post_files=int(res_dict.get("post_files", 0)),
            canary=int(res_dict.get("canary", 0)),
            canary_per=int(res_dict.get("canary_per", 0)),
            relro=int(res_dict.get("relro", 0)),
            relro_per=int(res_dict.get("relro_per", 0)),
            no_exec=int(res_dict.get("no_exec", 0)),
            no_exec_per=int(res_dict.get("no_exec_per", 0)),
            pie=int(res_dict.get("pie", 0)),
            pie_per=int(res_dict.get("pie_per", 0)),
            stripped=int(res_dict.get("stripped", 0)),
            stripped_per=int(res_dict.get("stripped_per", 0)),
            bins_checked=int(res_dict.get("bins_checked", 0)),
            strcpy=int(res_dict.get("strcpy", 0)),
            strcpy_bin=json.dumps(res_dict.get("strcpy_bin", {})),
            versions_identified=int(res_dict.get("versions_identified", 0)),
            cve_high=int(res_dict.get("cve_high", 0)),
            cve_medium=int(res_dict.get("cve_medium", 0)),
            cve_low=int(res_dict.get("cve_low", 0)),
            exploits=int(res_dict.get("exploits", 0)),
            metasploit_modules=int(res_dict.get("metasploit_modules", 0)),
            certificates=int(res_dict.get("certificates", 0)),
            certificates_outdated=int(res_dict.get("certificates_outdated", 0)),
        )
        res.save()
        return res
