import socket
import re
import paramiko
import subprocess
import time
import requests
import os
import json

from scp import SCPClient
from celery import shared_task
from celery.utils.log import get_task_logger
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.utils.timezone import now, timedelta
from django.conf import settings

from uploader.models import FirmwareAnalysis
from uploader.boundedexecutor import BoundedExecutor

from workers.models import Worker, Configuration
from workers.update.dependencies import DependencyType
from workers.update.update import exec_blocking_ssh, perform_update
from workers.orchestrator import get_orchestrator

logger = get_task_logger(__name__)

def create_periodic_tasks(**kwargs):
    """
    Create periodic tasks with the start of the application. (called in ready() method of the app config)
    """
    schedule, _created = IntervalSchedule.objects.get_or_create(
        every=2,
        period=IntervalSchedule.MINUTES
    )
    PeriodicTask.objects.get_or_create(
        interval=schedule,
        name='Update Worker Information',
        task='workers.tasks.update_worker_info',
    )


def update_system_info(configuration: Configuration, worker: Worker):
    """
    Update the system_info of a worker using the SSH credentials of the provided configuration to connect to the worker.

    :param configuration: Configuration object containing SSH credentials
    :param worker: Worker object to update

    :return: Dictionary containing system information

    :raises paramiko.SSHException: If the SSH connection fails or if any command execution fails
    """
    ssh_client = None

    try:
        ssh_client = worker.ssh_connect(configuration.id)

        os_info = exec_blocking_ssh(ssh_client, 'grep PRETTY_NAME /etc/os-release')
        os_info = os_info[len('PRETTY_NAME='):-1].strip('"')

        cpu_info = exec_blocking_ssh(ssh_client, 'nproc')
        cpu_info = cpu_info + " cores"

        ram_info = exec_blocking_ssh(ssh_client, 'free -h | grep Mem')
        ram_info = ram_info.split()[1]
        ram_info = ram_info.replace('Gi', 'GB').replace('Mi', 'MB')

        disk_str = exec_blocking_ssh(ssh_client, "df -h | grep '^/'")
        disk_str = disk_str.split('\n')[0].split()
        disk_total = disk_str[1].replace('G', 'GB').replace('M', 'MB')
        disk_free = disk_str[3].replace('G', 'GB').replace('M', 'MB')
        disk_info = f"Total: {disk_total}, Free: {disk_free}"

        version_regex = r"\d+\.\d+\.\d+[a-z]?"
        emba_version = exec_blocking_ssh(ssh_client, "sudo cat /root/emba/docker-compose.yml | awk -F: '/image:/ {print $NF; exit}'")
        emba_version = "N/A" if not re.match(version_regex, emba_version) else emba_version

        # 1) Try to access .git/HEAD which gets created after the initial clone
        # 2) If it does not exist, try to access FETCH_HEAD which only gets created after git pull or git fetch
        # 3) If neither FETCH_HEAD nor HEAD exist, we assume the feed has never been pulled
        date_regex = r"^\w{3} \d{1,2} \d{1,2}:\d{2}$"
        last_sync_nvd = exec_blocking_ssh(ssh_client, "sudo ls -l /root/emba/external/nvd-json-data-feeds/.git/FETCH_HEAD | awk '{print $6 \" \" $7 \" \" $8}'")
        if not re.match(date_regex, last_sync_nvd):
            last_sync_nvd = exec_blocking_ssh(ssh_client, "sudo ls -l /root/emba/external/nvd-json-data-feeds/.git/HEAD | awk '{print $6 \" \" $7 \" \" $8}'")
        last_sync_nvd = "N/A" if not re.match(date_regex, last_sync_nvd) else last_sync_nvd

        last_sync_epss = exec_blocking_ssh(ssh_client, "sudo ls -l /root/emba/external/EPSS-data/.git/FETCH_HEAD | awk '{print $6 \" \" $7 \" \" $8}'")
        if not re.match(date_regex, last_sync_epss):
            last_sync_epss = exec_blocking_ssh(ssh_client, "sudo ls -l /root/emba/external/EPSS-data/.git/HEAD | awk '{print $6 \" \" $7 \" \" $8}'")
        last_sync_epss = "N/A" if not re.match(date_regex, last_sync_epss) else last_sync_epss

        last_sync = f"NVD feed: {last_sync_nvd}, EPSS: {last_sync_epss}"

        ssh_client.close()

    except (paramiko.SSHException, socket.error) as ssh_error:
        if ssh_client:
            ssh_client.close()
        raise paramiko.SSHException("SSH connection failed") from ssh_error

    system_info = {
        'os_info': os_info,
        'cpu_info': cpu_info,
        'ram_info': ram_info,
        'disk_info': disk_info,
        'emba_version': emba_version,
        'last_sync': last_sync
    }
    worker.system_info = system_info
    worker.save()

    return system_info


@shared_task
def update_worker_info():
    """
    Task to update system information for all workers.
    """
    workers = Worker.objects.all()
    for worker in workers:
        config = worker.configurations.first()
        try:
            logger.info("Updating worker %s", worker.name)

            update_system_info(config, worker)

            if worker.analysis_id: # Check if analysis is truly running
                status = check_with_emba_log(worker)
                if status == AnalysisStatus.UNASSIGNED:
                    worker.analysis_id = None
                    worker.sync_enabled = False

                    worker_soft_reset(worker.id)
                    # TODO: Set as free in orchestrator

            worker.reachable = True
        except paramiko.SSHException:
            logger.info("Worker %s is unreachable, setting status to offline.", worker.name)
            worker.reachable = False
        except BaseException as error:
            logger.info("An error occurred while updating worker %s: %s", worker.name, error)
            continue
        finally:
            worker.save()


@shared_task
def sync_worker_analysis(worker_id, schedule_minutes=5):
    try:
        worker = Worker.objects.get(id=worker_id)

        if not worker.sync_enabled:
            PeriodicTask.objects.filter(name=f"sync_worker_{worker.id}").delete()
            raise RuntimeError(f"Sync is disabled. Removed the scheduled task.")

        logger.info(f"[Worker {worker.id}] Sync running...")
        status = fetch_analysis_logs(worker.id, worker.analysis_id)

        if status == "finished":
            worker.sync_enabled = False
            worker.analysis_id = None
            worker.save()

            PeriodicTask.objects.filter(name=f"sync_worker_{worker.id}").delete()

            worker_soft_reset(worker.id)

            # TODO: Set as free in orchestrator
            logger.info(f"[Worker {worker.id}] Analysis finished. Turned off sync.")

    except Exception as ex:
        print(f"[Worker {worker.id}] Unexpected exception: {ex}")
        return

def fetch_analysis_logs(worker_id, analysis_id):
    """
    Queues zip creation on remote worker, fetches it, extracts it and updates the database.
    It is a blocking function.
    Returns "finished" if the analysis completed and the scheduled task can be deleted.
    """
    try:
        worker = Worker.objects.get(id=worker_id)

        # FIXME: This assumes the same emba directory for the worker as the orchestrator
        remote_path = f"{settings.MEDIA_ROOT}/log_zip/{worker.analysis_id}.zip"
        local_path =  f"{settings.MEDIA_ROOT}/log_zip/{worker.analysis_id}.zip"

        config = worker.configurations.first()

        # Queue zip generation
        url = f"http://{worker.ip_address}:8001/uploader/queue_zip/"
        payload = { "analysis_id": worker.analysis_id }
        response = requests.post(url, json=payload)
        json_format = json.loads(response.text)

        if json_format["status"] == "error":
            msg = json_format["message"]
            raise ConnectionError(f"Could not queue zip generation on remote machine: {msg}")

        # Ensure log_zip/ exists
        os.makedirs(f"{settings.MEDIA_ROOT}/log_zip/", exist_ok=True)

        ssh_client = worker.ssh_connect()
        with SCPClient(ssh_client.get_transport()) as scp:
            scp.get(remote_path, local_path)

        BoundedExecutor.unzip_log(worker.analysis_id, local_path) # Blocking
        logger.info(f"[Worker {worker.id}] Unzipped to {local_path}.")

        if json_format["analysis_finished"]:
            return "finished"

    except Worker.DoesNotExist as ex:
        print(f"[Worker {worker.id}] Worker does not exist: {ex}")
    except Exception as ex:
        print(f"[Worker {worker.id}] Unexpected exception: {ex}")


# TODO Schedule this task after a worker starts an analysis
@shared_task
def check_with_emba_log(worker) -> Worker.AnalysisStatus:
    """
    Checks emba.log and infers the status of the analysis.
    Returns Worker.AnalysisStatus.UNASSIGNED or
            Worker.AnalysisStatus.RUNNING
    """
    try:
        client = worker.ssh_connect()

        cmd = (
            f"cd {settings.BASE_DIR} && "
            f"pipenv run python manage.py shell -c " # --quiet flag is not quiet enough
            f"'from uploader.models import FirmwareAnalysis; "
            f"print(FirmwareAnalysis.objects.get(id=\"{worker.analysis_id}\").pid)' | "
            f"tail -n 1"
        )
        _, stdout, stderr = client.exec_command(cmd)
        pid = stdout.read().decode().strip()

        path = f"{settings.EMBA_LOG_ROOT}/{worker.analysis_id}/emba_logs/emba.log"

        _, stdout, stderr = client.exec_command(f"tail -n 10 {path}")
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()

        if error:
            logger.error(f"[Worker {worker.id}] Error calling '$ tail {path}': {error}")

        if "Test ended on" in output:
            logger.info(f"[Worker {worker.id}] Analysis finished: {output}")
            # Kill emba Docker container if it's running
            client.exec_command(f"sudo kill {pid}")
            return Worker.AnalysisStatus.UNASSIGNED

        _, _, stderr = client.exec_command(f"kill -0 {pid}")

        error = stderr.read().decode().strip()

        if error: # ==  no running process
            logger.info(f"[Worker {worker.id}] EMBA container is no longer running.")
            return Worker.AnalysisStatus.UNASSIGNED

        # FIXME: It's possible a different process gets the same pid after emba

        logger.info(f"[Worker {worker.id}] Analysis is still running: {output}")
        return Worker.AnalysisStatus.RUNNING

    except Exception as ex:
        logger.error(f"[Worker {worker.id}] Unexpected exception: {ex}")

@shared_task
def start_analysis(worker_id, emba_cmd: str, src_path: str, target_path: str):
    """
    Copies the firmware image and triggers analysis start
    :params worker_id: the worker to use
    :params emba_cmd: The command to run
    :params src_path: img source path
    :params target_path: target path on worker
    """
    try:
        worker = Worker.objects.get(id=worker_id)
    except Worker.DoesNotExist:
        logger.error("start_analysis: Invalid worker id")
        return

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
    exec_blocking_ssh(client, "sudo rm -rf ./terminal.log")
    exec_blocking_ssh(client, f"sudo sh -c '{emba_cmd}' >./terminal.log 2>&1")


@shared_task
def update_worker(worker_id, dependency_idx):
    """
    Setup/Update an offline worker and add it to the orchestrator.

    DependencyType.ALL equals a full setup (e.g. new worker), all other DependencyType values are for specific dependencies (e.g. the external directory)

    :params worker_id: The worker to update
    :params dependency_idx: Dependency type as index
    """
    try:
        worker = Worker.objects.get(id=worker_id)
    except Worker.DoesNotExist:
        logger.error("start_analysis: Invalid worker id")
        return

    if dependency_idx not in DependencyType.__members__:
        logger.error("start_analysis: Invalid dependency type")
        return

    dependency = DependencyType[dependency_idx]

    logger.info("Worker update started (Dependency: %s)", dependency)

    worker.status = Worker.ConfigStatus.CONFIGURING
    worker.save()

    client = None

    orchestrator = get_orchestrator()
    try:
        # TODO: if the the worker is currently processing a job, this job should be cancelled here (or implicitly via remove_worker)
        orchestrator.remove_worker(worker)
        logger.info("Worker: %s removed from orchestrator", worker.name)
    except ValueError:
        pass

    try:
        client = worker.ssh_connect()
        if dependency == DependencyType.ALL:
            perform_update(worker, client, DependencyType.DEPS)
            perform_update(worker, client, DependencyType.REPO)
            perform_update(worker, client, DependencyType.EXTERNAL)
            perform_update(worker, client, DependencyType.DOCKERIMAGE)
        else:
            perform_update(worker, client, dependency)

        worker.status = Worker.ConfigStatus.CONFIGURED
        logger.info("Setup done")
    except Exception as ssh_error:
        logger.error("SSH connection failed: %s", ssh_error)
        worker.status = Worker.ConfigStatus.ERROR
    finally:
        if client is not None:
            client.close()
        worker.save()

    if worker.status == Worker.ConfigStatus.CONFIGURED:
        try:
            orchestrator.add_worker(worker)
            logger.info("Worker: %s added to orchestrator", worker.name)
        except ValueError:
            logger.error("Worker: %s already exists in orchestrator", worker.name)
