__copyright__ = 'Copyright 2025 The AMOS Projects'
__author__ = 'ashiven, ClProsser, Luka Dekanozishvili, SirGankalot'
__license__ = 'MIT'

import ipaddress
import os
import re
import time
import socket
import subprocess
from functools import partial
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import requests
import paramiko
from redis import Redis

from celery import shared_task
from celery.utils.log import get_task_logger
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.db.models import Count
from django.utils.timezone import make_aware
from django.utils import timezone
from django.conf import settings

from embark.helper import is_ip_local_host
from workers.models import Worker, Configuration, DependencyVersion, DependencyType, WorkerDependencyVersion
from workers.update.dependencies import eval_outdated_dependencies, get_script_name, update_dependency, setup_dependency
from workers.update.update import exec_blocking_ssh, parse_deb_list, process_update_queue, init_sudoers_file, update_dependencies_info, setup_ssh_key, undo_ssh_key, undo_sudoers_file
from workers.orchestrator import get_orchestrator
from workers.codeql_ignore import new_autoadd_client
from uploader.models import FirmwareAnalysis, FirmwareFile
from uploader.executor import submit_firmware

logger = get_task_logger(__name__)

REDIS_CLIENT = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
LOCK_TIMEOUT = 60 * 5


def create_periodic_tasks(**kwargs):
    """
    Create periodic tasks with the start of the application. (called in ready() method of the app config)
    """
    schedule_2m, _ = IntervalSchedule.objects.get_or_create(
        every=2, period=IntervalSchedule.MINUTES
    )

    PeriodicTask.objects.get_or_create(
        interval=schedule_2m,
        name="Update Worker Information",
        task="workers.tasks.update_worker_info",
    )


def update_system_info(worker: Worker):
    """
    Update the system_info of a worker using the SSH credentials of the provided configuration to connect to the worker.

    :param worker: Worker object to update
    :return: Dictionary containing system information
    :raises paramiko.SSHException: If the SSH connection fails or if any command execution fails
    """
    system_info = {}
    ssh_client = None
    worker.write_log(f"\nUpdating system info...\n")
    try:
        ssh_client = worker.ssh_connect(timeout=10)

        os_info = exec_blocking_ssh(ssh_client, 'grep PRETTY_NAME /etc/os-release', worker.write_log)
        os_info = os_info[len('PRETTY_NAME='):-1].strip('"')

        cpu_info = exec_blocking_ssh(ssh_client, 'nproc')
        cpu_info = cpu_info + " cores"

        ram_info = exec_blocking_ssh(ssh_client, 'free -h | grep Mem')
        ram_info = ram_info.split()[1]
        ram_info = ram_info.replace('Gi', 'GB').replace('Mi', 'MB')

        disk_str = exec_blocking_ssh(ssh_client, "df -h | grep '^/'")
        disk_str = disk_str.splitlines()[0].split()
        disk_total = disk_str[1].replace('G', 'GB').replace('M', 'MB')
        disk_free = disk_str[3].replace('G', 'GB').replace('M', 'MB')
        disk_info = f"Free: {disk_free}  Total: {disk_total}"

        system_info = {
            'os_info': os_info,
            'cpu_info': cpu_info,
            'ram_info': ram_info,
            'disk_info': disk_info
        }
        worker.system_info = system_info

    except paramiko.SSHException as ssh_error:
        raise paramiko.SSHException(f"Failed to connect while updating system info for worker: {worker.name}: {ssh_error}") from ssh_error
    except BaseException as error:
        logger.error("An error occurred while updating system info for worker %s: %s", worker.name, error)
        worker.write_log(f"\nError: An error occurred while updating system info: {error}\n")
        raise BaseException("Failed to update system info") from error
    finally:
        if ssh_client:
            ssh_client.close()
        worker.save()
    return system_info


def _new_analysis_from(old_analysis: FirmwareAnalysis) -> FirmwareAnalysis:
    """
    Creates a new FirmwareAnalysis object based on the provided old_analysis.
    This can be used to restart a cancelled or failed analysis on a different worker
    with the same settings and parameters as the original analysis.

    The settings that the user chooses in the FirmwareAnalysisForm will be copied over,
    everything else may have changed and will be created anew.

    After the new analysis is created, the old one will be deleted.

    :param old_analysis: The original FirmwareAnalysis object to duplicate
    """
    new_analysis = FirmwareAnalysis(
        user=old_analysis.user,
        firmware=old_analysis.firmware,
        firmware_name=old_analysis.firmware_name,
        version=old_analysis.version,
        notes=old_analysis.notes,
        firmware_Architecture=old_analysis.firmware_Architecture,
        user_emulation_test=old_analysis.user_emulation_test,
        system_emulation_test=old_analysis.system_emulation_test,
        sbom_only_test=old_analysis.sbom_only_test,
        scan_modules=old_analysis.scan_modules,
    )
    new_analysis.save()
    new_analysis.device.set(old_analysis.device.all())

    logger.info("Created new analysis %s from old analysis %s", new_analysis.id, old_analysis.id)
    logger.info("New analysis for firmware file: %s", new_analysis.firmware.id)

    # NOTE:
    # - This triggers uploader/models::delete_analysis_pre_delete() which tries to delete the log directory at
    #   old_analysis.path_to_logs if the logs haven't been archived and it is a valid path in settings.EMBA_LOG_ROOT.
    #   If they have been archived (old_analysis.archived=True), the archived logs (old_analysis.zip_file) will be deleted.
    # - We may want to set keep_parents=True in case the analysis is still referenced by a parent object.
    #   This is how it was previously done in dashboard/views::delete_analysis().
    # - We don't need to worry about an unterminated LogReader.read_loop() since this only gets started for local analyses
    #   via BoundedExecutor.submit() of LogReader.__init__() with the analysis ID.
    # - Since we assume that the old analysis was running on an unreachable worker, we don't need to check
    #   if the analysis is still running (old_analysis.finished) but we do need to reset the worker once it becomes reachable again.
    # - We have to explicitly reset the worker once it reconnects because the monitoring task
    #   which would usually reset the worker when an analysis failed or finished will not be able to reach the worker.
    # old_analysis.delete(keep_parents=True)  Don't uncomment. Since we are now calling this function from the monitoring task, we still need the old analysis.

    return new_analysis


@shared_task
def setup_reconnected_worker_task(worker_id):
    """
    Handle a worker that was marked as unreachable but has now reconnected.
    This will soft reset the worker, perform any queued updates, and re-add it to the orchestrator.
    :param worker_id: The worker to setup
    """
    try:
        worker = Worker.objects.get(id=worker_id)
    except Worker.DoesNotExist:
        logger.error("start_analysis: Invalid worker id")
        return

    logger.info("Reconnecting worker: %s", worker.name)
    worker.write_log(f"\nReconnecting worker...\n")

    worker_soft_reset_task(worker.id)
    process_update_queue(worker)

    if worker.status == Worker.ConfigStatus.CONFIGURED:
        try:
            orchestrator = get_orchestrator()
            orchestrator.add_worker(worker)
            orchestrator.assign_tasks()
        except ValueError:
            logger.error("Reconnected worker: %s already registered in the orchestrator", worker.name)
            worker.write_log(f"\nWarning: Worker already registered in the orchestrator\n")


def _handle_unreachable_worker(worker: Worker, force: bool = False):
    """
    If a worker node has been unresponsive for the last settings.WORKER_REACHABLE_TIMEOUT minutes,
    set its reachable status to False and remove it from the orchestrator.
    Any analysis which was running on the worker will be rescheduled to another worker.

    :param worker: The worker to handle
    :param force: If True, the worker will be set to unreachable even if the reachable timeout has not been exceeded.
    """
    with REDIS_CLIENT.lock(f"HANDLE_UNREACHABLE_WORKER__{worker.ip_address}", LOCK_TIMEOUT):
        worker.refresh_from_db()
        if not worker.reachable:
            # Unreachable worker has already been dealt with
            return

        logger.info("Handling unreachable worker: %s", worker.name)
        worker.write_log(f"\nHandling unreachable worker...\n")

        try:
            reachable_threshold = make_aware(datetime.now()) - timedelta(minutes=settings.WORKER_REACHABLE_TIMEOUT)
            if worker.last_reached < reachable_threshold or force:
                worker.reachable = False
                logger.info("Failed to reach worker %s for the last %d minutes, setting status to unreachable.", worker.name, settings.WORKER_REACHABLE_TIMEOUT)
                worker.write_log(f"\nWorker failed to reach timeout threshold, marking as unreachable\n")

                # We need this because the analysis_id will be set to None in orchestrator.remove_worker
                # We also have to remove the worker before reassigning the analysis
                reassign_analysis_id = worker.analysis_id

                orchestrator = get_orchestrator()
                orchestrator.remove_worker(worker, check=False)

                if reassign_analysis_id:
                    logger.info("Reassigning analysis %s of unreachable worker %s", reassign_analysis_id, worker.name)
                    worker.write_log(f"\nReassigning analysis {reassign_analysis_id} to another worker\n")
                    firmware_analysis = FirmwareAnalysis.objects.get(id=reassign_analysis_id)
                    firmware_file = FirmwareFile.objects.get(id=firmware_analysis.firmware.id)
                    new_analysis = _new_analysis_from(firmware_analysis)
                    submit_firmware(new_analysis, firmware_file)
        except BaseException as error:
            logger.error("An error occurred while handling unreachable worker %s: %s", worker.name, error)
            worker.write_log(f"\nError occurred while handling unreachable worker: {error}\n")
        finally:
            worker.save()


@shared_task
def update_worker_info():
    """
    Task to update system information for all workers and handle worker disconnections/reconnections.
    """
    lock = REDIS_CLIENT.lock("UPDATE_WORKER_INFO_LOCK", LOCK_TIMEOUT)
    if lock.locked():
        logger.info("update_worker_info: Skipped, as previous task still running")
        return

    with lock:
        workers = Worker.objects.all()
        for worker in workers:
            try:
                logger.info("Updating system info: %s", worker.name)
                worker.write_log(f"\nUpdating system info...\n")
                update_system_info(worker)

                # The worker was previously set to unreachable and is now reachable again
                if not worker.reachable:
                    setup_reconnected_worker_task.delay(worker.id)

                worker.last_reached = make_aware(datetime.now())
                worker.reachable = True
            except paramiko.SSHException:
                _handle_unreachable_worker(worker)
            except BaseException as error:
                logger.error("An error occurred while updating worker %s: %s", worker.name, error)
                worker.write_log(f"\nError occurred while updating worker: {error}\n")
                continue
            finally:
                worker.save()


@shared_task
def start_analysis(worker_id, emba_cmd: str, src_path: str, target_path: str):
    """
    Copies the firmware image and triggers analysis start
    :param worker_id: the worker to use
    :param emba_cmd: The command to run
    :param src_path: img source path
    :param target_path: target path on worker
    """
    try:
        worker = Worker.objects.get(id=worker_id)
    except Worker.DoesNotExist:
        logger.error("start_analysis: Invalid worker id")
        return

    worker.write_log(f"\nStarting firmware analysis...\n")
    client = worker.ssh_connect()

    exec_blocking_ssh(client, f"sudo rm -rf {settings.WORKER_FIRMWARE_DIR}")
    exec_blocking_ssh(client, f"sudo mkdir -p {settings.WORKER_FIRMWARE_DIR}")

    target_path_user = target_path if client.ssh_user == "root" else f"/home/{client.ssh_user}/temp"

    sftp_client = client.open_sftp()
    sftp_client.put(src_path, target_path_user)
    sftp_client.close()

    if client.ssh_user != "root":
        exec_blocking_ssh(client, f"sudo mv {target_path_user} {target_path}")

    exec_blocking_ssh(client, f"sudo rm -rf {settings.WORKER_EMBA_LOGS}")
    exec_blocking_ssh(client, "sudo rm -rf /root/emba_run.log")
    client.exec_command(f"sudo sh -c '{emba_cmd}' >./emba_run.log 2>&1")  # nosec
    logger.info("Firmware analysis has been started on the worker.")
    worker.write_log(f"\nFirmware analysis has been started on the worker.\n")

    # Create file to suppress errors
    os.makedirs(f"{settings.EMBA_LOG_ROOT}/{worker.analysis_id}/emba_logs/", exist_ok=True)
    open(f"{settings.EMBA_LOG_ROOT}/{worker.analysis_id}/emba_logs/emba.log", "a").close()  # pylint: disable=unspecified-encoding, consider-using-with
    time.sleep(10)  # Give the Docker container time to start up

    monitor_worker_and_fetch_logs.delay(worker.id)


@shared_task
def monitor_worker_and_fetch_logs(worker_id) -> None:
    """
    Loops until the analysis stops on the remote worker.
    Zips the analysis logs on the remote worker, downloads and extracts them.
    If the worker is finished, performs a soft reset.

    :param worker_id: ID of worker to monitor and fetch logs for.
    """
    try:
        worker = Worker.objects.get(id=worker_id)
        analysis = FirmwareAnalysis.objects.get(id=worker.analysis_id)
    except (Worker.DoesNotExist, FirmwareAnalysis.DoesNotExist):
        logger.error("[Worker %s] Invalid worker or analysis ID.", worker_id)
        return

    ssh_failed = False
    orchestrator = get_orchestrator()
    try:
        while True:
            _fetch_analysis_logs(worker)
            is_running = _is_emba_running(worker)
            analysis = FirmwareAnalysis.objects.get(id=worker.analysis_id)
            analysis_finished = analysis.finished or analysis.status["finished"]

            if not is_running or analysis_finished or not orchestrator.is_busy(worker):
                logger.info("[Worker %s] Analysis finished.", worker.id)
                worker.write_log(f"\nAnalysis finished\n")
                return
            time.sleep(1)
    except paramiko.SSHException as ssh_error:
        logger.error("[Worker %s] SSH connection failed while monitoring: %s", worker.id, ssh_error)
        worker.write_log(f"\nSSH connection failed while monitoring: {ssh_error}\n")
        _handle_unreachable_worker(worker, force=True)
        analysis.failed = True
        ssh_failed = True
    except Exception as exception:
        logger.error("[Worker %s] Monitoring failed, stopping the task. Exception: %s", worker.id, exception)
        worker.write_log(f"\nMonitoring failed: {exception}\n")
        analysis.failed = True
    finally:
        analysis.finished = True
        analysis.status['finished'] = True
        analysis.status['work'] = False
        analysis.end_date = timezone.now()
        analysis.scan_time = timezone.now() - analysis.start_date
        analysis.duration = str(analysis.scan_time)
        analysis.save()

        if not ssh_failed:
            orchestrator.remove_worker(worker)

            worker_soft_reset_task(worker.id, True)
            process_update_queue(worker)

            if worker.status == Worker.ConfigStatus.CONFIGURED:
                orchestrator.add_worker(worker)

            orchestrator.assign_tasks()


def _fetch_analysis_logs(worker) -> None:
    """
    Zips the analysis log files on remote worker, downloads it, extracts it.
    Also gets the emba_run.log file that's displayed in the UI

    :param worker: Worker object whose analysis_id logs to process.
    :raises CalledProcessError: If extracting the zipfile fails.
    """
    client = None
    sftp_client = None
    try:
        client = worker.ssh_connect()

        # To not error if the logs dir has been deleted
        exec_blocking_ssh(client, f"sudo mkdir -p {settings.WORKER_EMBA_LOGS}")

        homedir = "/root" if client.ssh_user == "root" else f"/home/{client.ssh_user}"
        remote_zip_path = f"{homedir}/emba_logs.zip"

        logger.info("[Worker %s] Zipping logs on remote...", worker.id)
        worker.write_log(f"\nZipping logs on remote...\n")
        zip_cmd = (
            f'sudo bash -c "cd /root && '
            f"7z u -t7z -y {remote_zip_path} {settings.WORKER_EMBA_LOGS} -uq3; "
            f'chown {client.ssh_user}: {remote_zip_path}"'
        )
        exec_blocking_ssh(client, zip_cmd)
        logger.info("[Worker %s] Zipping logs on remote complete.", worker.id)
        worker.write_log(f"\nZipping logs on remote complete.\n")

        # Ensure dirs exists locally
        local_log_dir = f"{settings.EMBA_LOG_ROOT}/{worker.analysis_id}"
        os.makedirs(f"{local_log_dir}/emba_logs/", exist_ok=True)
        os.makedirs(f"{settings.MEDIA_ROOT}/log_zip/", exist_ok=True)

        # Fetch zip file
        local_zip_path = f"{settings.MEDIA_ROOT}/log_zip/{worker.analysis_id}.zip"
        sftp_client = client.open_sftp()
        sftp_client.get(f"{homedir}/emba_logs.zip", local_zip_path)
        logger.info("[Worker %s] Downloaded the log zip.", worker.id)
        worker.write_log(f"\nDownloaded the log zip.\n")

        # Ensure emba_run.log can be accessed by the user
        if client.ssh_user != "root":
            chown_cmd = f'sudo bash -c "chown {client.ssh_user}: {homedir}/emba_run.log"'
            exec_blocking_ssh(client, chown_cmd)

        sftp_client.get(f"{homedir}/emba_run.log", f"{local_log_dir}/emba_run.log")

        logger.info("[Worker %s] Downloaded emba_run.log.", worker.id)
        worker.write_log(f"\nDownloaded emba_run.log.\n")

        # Note: The LogReader.read_loop() will look for logfiles in <analysis.path_to_logs>/emba.log
        #       where path_to_logs will be set to settings.EMBA_LOG_ROOT/<analysis.id>/emba_logs/
        unzip_cmd = ["7z", "x", "-y", local_zip_path, f"-o{local_log_dir}/"]
        subprocess.run(unzip_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)  # nosec

        logger.info("[Worker %s] Unzipped the log zip to: %s/emba_logs/", worker.id, local_log_dir)
        worker.write_log(f"\nUnzipped the log zip.\n")

    finally:
        if sftp_client is not None:
            sftp_client.close()
        if client is not None:
            client.close()


def _is_emba_running(worker) -> bool:
    """
    Checks if an EMBA Docker container is running on the worker.

    :param worker: The worker to check.
    :return: True, if EMBA is still running,
             False, otherwise
    """
    client = None
    try:
        client = worker.ssh_connect()

        cmd = "sudo docker ps -a | grep emba || true"
        output = exec_blocking_ssh(client, cmd)
        if not output:
            logger.info("[Worker %s] EMBA Docker container is no longer running.", worker.id)
            worker.write_log(f"\nEMBA Docker container is no longer running.\n")
            return False

        return True

    except Exception as exception:
        logger.error("[Worker %s] Unexpected exception: %s", worker.id, exception)
        worker.write_log(f"\nUnexpected exception while checking if EMBA is running: {exception}\n")
        return False
    finally:
        if client is not None:
            client.close()


@shared_task
def stop_remote_analysis(worker_id) -> None:
    """
    Stops the EMBA Docker container. Fetches the logs for the
    last time and releases the worker in the orchestrator.

    :param worker_id: ID of worker whose analysis to stop.
    """
    client = None
    try:
        worker = Worker.objects.get(id=worker_id)
        if not _is_emba_running(worker):
            logger.error("[Worker %s] Failed to stop analysis: EMBA container isn't running.", worker.id)
            worker.write_log(f"\nFailed to stop analysis: EMBA container isn't running.\n")
            return

        client = worker.ssh_connect()

        logger.info("[Worker %s] Trying to stop the analysis.", worker.id)
        worker.write_log(f"\nTrying to stop the analysis.\n")

        docker_cmd = "sudo docker ps | grep emba | awk '{print $1;}' | xargs -I {} sudo docker stop {}"
        exec_blocking_ssh(client, docker_cmd)

        analysis = FirmwareAnalysis.objects.get(id=worker.analysis_id)
        analysis.failed = True
        analysis.finished = True
        analysis.status['finished'] = True
        analysis.status['work'] = False
        analysis.end_date = timezone.now()
        analysis.scan_time = timezone.now() - analysis.start_date
        analysis.duration = str(analysis.scan_time)
        analysis.save()

        logger.info("[Worker %s] Successfully stopped the analysis.", worker.id)
        worker.write_log(f"\nSuccessfully stopped the analysis.\n")

    except Exception as exception:
        logger.error("[Worker %s] Error while stopping analysis: %s", worker.id, exception)
        worker.write_log(f"\nError while stopping analysis: {exception}\n")
    finally:
        if client is not None:
            client.close()


@shared_task
def update_worker(worker_id):
    """
    Setup/Update an offline worker and add it to the orchestrator.

    :params worker_id: The worker to update
    """
    try:
        worker = Worker.objects.get(id=worker_id)
    except Worker.DoesNotExist:
        logger.error("update_worker: Invalid worker id")
        return

    logger.info("update_worker: Worker update task started")

    orchestrator = get_orchestrator()
    orchestrator.remove_worker(worker, False)

    process_update_queue(worker)

    if worker.status == Worker.ConfigStatus.CONFIGURED:
        try:
            update_system_info(worker)
            orchestrator.add_worker(worker)
            orchestrator.assign_tasks()
        except ValueError:
            logger.error("Worker: %s already exists in orchestrator", worker.name)
            worker.write_log(f"\nWarning: Worker already exists in orchestrator\n")


@shared_task
def fetch_dependency_updates():
    """
    Checks if there are updates available
    """
    logger.info("Dependency update check started.")

    version = DependencyVersion.objects.first()
    if not version:
        version = DependencyVersion()

    DOCKER_COMPOSE_URL = "https://raw.githubusercontent.com/e-m-b-a/emba/refs/heads/master/docker-compose.yml"  # pylint: disable=invalid-name
    GH_API_URL = "https://api.github.com/repos/{}/commits?per_page=1"  # pylint: disable=invalid-name

    def _get_head_time(repo):
        try:
            response = requests.get(GH_API_URL.format(repo), timeout=30)
            json_response = response.json()

            return json_response[0]["sha"], json_response[0]["commit"]["author"]["date"]
        except requests.exceptions.Timeout as exception:
            logger.error("Update check: Failed. An error occured on contacting GH API: %s", exception)
        except (requests.exceptions.JSONDecodeError, KeyError):
            logger.error("Update check: Failed. GH API returned invalid or incomplete json: %s", response.text)
        return "latest", None

    # Fetch EMBA + docker image
    try:
        response = requests.get(DOCKER_COMPOSE_URL, timeout=30)
        match = re.search(r'image:\s?embeddedanalyzer\/emba:(.*?)\n', response.text)

        if match is None:
            logger.error("Update check: Failed. EMBA docker-compose.yml does not contain image version")
            version.emba = "latest"
        else:
            version.emba = match.group(1)
            version.emba_head, _ = _get_head_time("e-m-b-a/emba")
    except requests.exceptions.Timeout as exception:
        logger.error("Update check: Failed. An error occured on contacting GH API for docker-compose.yml: %s", exception)
        version.emba = "latest"

    # Fetch external
    version.nvd_head, version.nvd_time = _get_head_time("EMBA-support-repos/nvd-json-data-feeds")
    version.epss_head, version.epss_time = _get_head_time("EMBA-support-repos/EPSS-data")

    # Fetch APT
    Path(settings.WORKER_SETUP_LOGS_ABS).mkdir(parents=True, exist_ok=True)

    log_file = settings.WORKER_SETUP_LOGS_ABS.format(timestamp=int(time.time()))
    logger.info("APT dependency update check started. Logs: %s", log_file)
    try:
        script_path = os.path.join(os.path.dirname(__file__), "update", get_script_name(DependencyType.DEPS))
        cmd = f"sudo {script_path} '{settings.WORKER_UPDATE_CHECK}' ''"
        with open(log_file, "w+", encoding="utf-8") as file:
            with subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=file, stderr=file, shell=True) as proc:  # nosec
                proc.communicate()

            if proc.returncode == 0:
                logger.info("APT dependency update check successful. Logs: %s", log_file)
            else:
                logger.error("APT dependency update check failed. Logs: %s", log_file)

        deb_list_str = subprocess.check_output(f"cd {os.path.join(settings.WORKER_UPDATE_CHECK, 'pkg')} && sha256sum *.deb", shell=True)  # nosec
        version.deb_list = parse_deb_list(deb_list_str.decode('utf-8'))

        update_dependency(DependencyType.DEPS, False)
        setup_dependency(DependencyType.DEPS, "cached")
        update_dependency(DependencyType.DEPS, True)
    except BaseException as exception:
        logger.error("Error APT dependency update check: %s. Logs: %s", exception, log_file)
        version.deb_list = {}

    # Store in DB
    version.save()

    # Evaluate for each worker
    workers = Worker.objects.all()
    for worker in workers:
        eval_outdated_dependencies(worker)


@shared_task
def worker_soft_reset_task(worker_id, only_reset=False):
    """
    Removes the worker from the orchestrator, reassigns the analysis if needed,
    connects via SSH to the worker and performs the soft reset, and re-adds the worker to the orchestrator.

    :param worker_id: ID of worker to soft reset
    :param only_reset: If True, only performs the reset without reassigning the analysis or removing the worker from the orchestrator.
    """
    ssh_client = None
    try:
        worker = Worker.objects.get(id=worker_id)
        if not only_reset:
            reassign_analysis_id = worker.analysis_id

            # Remove the worker from the orchestrator
            orchestrator = get_orchestrator()
            orchestrator.remove_worker(worker, check=False)

            # Reassign the analysis running on the worker
            if reassign_analysis_id:
                firmware_analysis = FirmwareAnalysis.objects.get(id=reassign_analysis_id)
                firmware_file = FirmwareFile.objects.get(id=firmware_analysis.firmware.id)
                new_analysis = _new_analysis_from(firmware_analysis)
                submit_firmware(new_analysis, firmware_file)

        # Soft reset the worker
        ssh_client = worker.ssh_connect()
        homedir = "/root" if ssh_client.ssh_user == "root" else f"/home/{ssh_client.ssh_user}"
        exec_blocking_ssh(ssh_client, "sudo docker ps -aq | xargs -r sudo docker stop | xargs -r sudo docker rm || true")
        exec_blocking_ssh(ssh_client, f"sudo rm -rf {settings.WORKER_EMBA_LOGS}")
        exec_blocking_ssh(ssh_client, f"sudo rm -rf {settings.WORKER_FIRMWARE_DIR}")
        exec_blocking_ssh(ssh_client, f"sudo rm -rf {homedir}/emba_logs.zip*")  # Also delete possible leftover tmp files
        exec_blocking_ssh(ssh_client, f"sudo rm -rf {homedir}/emba_run.log")

        if not only_reset:
            # Re-add the worker to the orchestrator
            try:
                orchestrator.add_worker(worker)
            except ValueError:
                pass
    except Worker.DoesNotExist:
        logger.error("Worker Soft Reset: Invalid worker id")
    except (paramiko.SSHException, socket.error):
        logger.error("[Worker %s] SSH Connection failed while soft resetting.", worker.id)
        worker.write_log(f"\nSSH Connection failed while soft resetting.\n")
    finally:
        if ssh_client is not None:
            ssh_client.close()


@shared_task
def worker_hard_reset_task(worker_id):
    try:
        worker = Worker.objects.get(id=worker_id)
    except Worker.DoesNotExist:
        logger.error("Worker Hard Reset: Invalid worker id")
        worker.write_log(f"\nWorker Hard Reset: Invalid worker id\n")
        return

    orchestrator = get_orchestrator()
    orchestrator.remove_worker(worker, False)

    worker_soft_reset_task(worker_id, True)

    ssh_client = None
    try:
        worker.status = Worker.ConfigStatus.UNCONFIGURED
        worker.save()

        ssh_client = worker.ssh_connect()
        emba_path = os.path.join(settings.WORKER_EMBA_ROOT, "full_uninstaller.sh")
        exec_blocking_ssh(ssh_client, "sudo bash " + emba_path)
        ssh_client.close()
        update_dependencies_info(worker)
    except paramiko.SSHException:
        logger.error("SSH Connection didnt work for: %s", worker.name)
        worker.write_log(f"\nSSH Connection didnt work for hard reset.\n")
        if ssh_client:
            ssh_client.close()


@shared_task
def delete_config_task(config_id):
    """
    Deletes config and all assosiated workers (if not linked in another config)
    :param config_id: The config to delete
    """
    try:
        config = Configuration.objects.get(id=config_id)
        config.write_log(f"\nDeleting configuration...\n")
    except Configuration.DoesNotExist:
        logger.error("delete_config: Configuration %s not found", config_id)

    orchestrator = get_orchestrator()
    single_config_workers = Worker.objects.annotate(config_count=Count('configurations')).filter(configurations__id=config_id, config_count=1)
    for worker in single_config_workers:
        orchestrator.remove_worker(worker, False)

    config_workers = Worker.objects.filter(configurations__id=config.id)
    for worker in config_workers:
        undo_ssh_key(config, worker)
        undo_sudoers_file(config, worker)

    config.delete_ssh_keys()

    for worker in single_config_workers:
        worker.dependency_version.delete()
        worker.delete()

    if os.path.exists(config.log_location):
        os.remove(config.log_location)

    config.delete()


def _update_or_create_worker(config: Configuration, ip_address: str):
    """
    Creates a worker DB entry for a given IP address or updates the existing one.

    :param config: The configuration the worker belongs to
    :param ip_address: The IP address of the worker
    """
    worker = None
    try:
        worker = Worker.objects.get(ip_address=ip_address)
        if config not in worker.configurations.all():
            worker.configurations.add(config)
            worker.save()
    except Worker.DoesNotExist:
        config.write_log(f"Creating new worker for IP address {ip_address}\n")
        version = WorkerDependencyVersion()
        version.save()
        worker = Worker(
            dependency_version=version,
            name=f"worker-{ip_address}",
            ip_address=ip_address,
            system_info={},
            reachable=True
        )
        worker.save()
        # create log file
        if not Path(os.path.join(settings.WORKER_LOG_ROOT_ABS,settings.WORKER_WORKER_LOGS)).exists():
            Path(os.path.join(settings.WORKER_LOG_ROOT_ABS,settings.WORKER_WORKER_LOGS)).mkdir(parents=True, exist_ok=True)
        worker.log_location = Path(f"{os.path.join(settings.WORKER_LOG_ROOT_ABS, settings.WORKER_WORKER_LOGS)}/{worker.id}.log")
        worker.write_log(f"\nCreated new worker for IP address {ip_address}\n")
        worker.configurations.set([config])
        worker.save()
        config.write_log(f"New worker created with ID {worker.id} for IP address {ip_address}\n")
    finally:
        try:
            # TODO: The first two function calls may cause issues when a config
            #       is re-scanned after its first successful scan
            init_sudoers_file(config, worker)
            setup_ssh_key(config, worker)
            update_system_info(worker)
            update_dependencies_info(worker)
        except BaseException:
            pass


def _scan_for_worker(config: Configuration, ip_address: str, port: int = 22, timeout: int = 1, ssh_auth_check: bool = True) -> str:
    """
    Checks if a host is reachable, has valid SSH creds, and sudo perms.
    Updates the DB accordingly.

    :param config: Config template
    :param ip_address: Host's IP address
    :param port: SSH port (default: 22)
    :param timeout: Connection timeout in seconds
    :param ssh_auth_check: If True, tries to connect to the ip address with the config's ssh credentials and checks whether the user has sudo privileges
    :return: ip_address on success, None otherwise
    """
    config.write_log(f"Scanning IP address: {ip_address}")
    try:  # Check TCP socket first before trying SSH
        with socket.create_connection((ip_address, port), timeout):
            pass
    except TimeoutError:
        config.write_log(f"Host {ip_address} is not reachable (timeout).")
        logger.error("[%s@%s] Host is not reachable (timeout).", config.ssh_user, ip_address)
        return None
    except Exception as exc:
        logger.error("[%s@%s] Cannot connect to host: %s", config.ssh_user, ip_address, exc)
        config.write_log(f"Cannot connect to host {config.ssh_user}@{ip_address}: {exc}")
        return None

    client = None
    try:
        # We only want to perform this check for newly created configs, not for scans of existing configs
        # (ssh pw auth would have been disabled for workers belonging to existing configs)
        if ssh_auth_check:
            client = new_autoadd_client()
            client.connect(
                ip_address, port=port,
                username=config.ssh_user, password=config.ssh_password,
                timeout=timeout
            )

            logger.info("[%s@%s] Connected via SSH. Now testing for sudo privileges.", config.ssh_user, ip_address)
            config.write_log(f"[{config.ssh_user}@{ip_address}] Connected via SSH. Now testing for sudo privileges.")

            stdin, stdout, _ = client.exec_command("sudo -v", get_pty=True)  # nosec
            stdin.write(config.ssh_password + "\n")
            stdin.flush()
            if stdout.channel.recv_exit_status():
                logger.info("[%s@%s] Can't register worker: No sudo permission.", config.ssh_user, ip_address)
                config.write_log(f"[{config.ssh_user}@{ip_address}] Can't register worker: No sudo permission.")
                # Delete worker if SSH configuration changed
                Worker.objects.filter(ip_address=ip_address).delete()
                return None

        _update_or_create_worker(config, ip_address)
        logger.info("[%s@%s] Worker is reachable via SSH.", config.ssh_user, ip_address)
        config.write_log(f"[{config.ssh_user}@{ip_address}] Worker is reachable via SSH.")
        return ip_address

    except Exception as exc:
        logger.error("[%s@%s] Exception while scanning worker: %s", config.ssh_user, ip_address, exc)
        config.write_log(f"[{config.ssh_user}@{ip_address}] Exception while scanning worker: {exc}")
        return None
    finally:
        if client is not None:
            client.close()


@shared_task
def config_worker_scan_task(configuration_id: int):
    """
    Scan the IP range of a given configuration and create/update correctly setup workers.

    :param configuration_id: ID of the configuration to scan
    """
    try:
        config = Configuration.objects.get(id=configuration_id)
        logger.info("config_worker_scan_task: Starting scan for configuration %s", config.name)
        config.write_log("Starting worker scan task.")
        ssh_auth_check = not config.scan_status == Configuration.ScanStatus.FINISHED
        config.scan_status = Configuration.ScanStatus.SCANNING
        config.save()

        ip_network = ipaddress.ip_network(config.ip_range, strict=False)
        ip_addresses = [str(ip) for ip in ip_network.hosts() if not is_ip_local_host(str(ip))]  # filter out local host IPs
        logger.info("Scanning IPs: %s", ip_addresses)
        config.write_log(f"Scanning IPs: {ip_addresses}")
        with ThreadPoolExecutor(max_workers=50) as executor:
            results = executor.map(partial(_scan_for_worker, config, ssh_auth_check=ssh_auth_check), ip_addresses)
            reachable = set(results) - {None}

        unreachable_workers = [worker for worker in config.workers.all() if worker.ip_address not in reachable]
        for worker in unreachable_workers:
            _handle_unreachable_worker(worker)

        config.write_log(f"Worker scan task finished. {len(reachable)} reachable workers found.")
        config.scan_status = Configuration.ScanStatus.FINISHED
        logger.info("config_worker_scan_task: Scan finished for configuration %s. %d reachable", config.name, len(reachable))
    except ValueError as ve:
        logger.error("config_worker_scan_task: Invalid IP range specified: %s", ve)
        config.write_log(f"Worker scan task failed: Invalid IP range specified: {ve}")
        config.scan_status = Configuration.ScanStatus.ERROR
    except Configuration.DoesNotExist:
        logger.error("config_worker_scan_task: Invalid configuration id")
        # config is not defined here, so skip write_log and scan_status
    except BaseException as error:
        logger.error("config_worker_scan_task: An error occurred while scanning workers: %s", error)
        config.write_log(f"Worker scan task failed: {error}")
        config.scan_status = Configuration.ScanStatus.ERROR
    finally:
        config.save()
