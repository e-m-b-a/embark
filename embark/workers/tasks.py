import os
import re
import socket
import subprocess

import paramiko

from celery import shared_task
from celery.utils.log import get_task_logger
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.conf import settings

from workers.models import Worker, Configuration
from workers.update.dependencies import DependencyType
from workers.update.update import exec_blocking_ssh, perform_update
from workers.orchestrator import get_orchestrator
from uploader.models import FirmwareAnalysis
from uploader.boundedexecutor import BoundedExecutor
from embark.logreader import LogReader

logger = get_task_logger(__name__)


def create_periodic_tasks(**kwargs):
    """
    Create periodic tasks with the start of the application. (called in ready() method of the app config)
    """
    schedule_2m, _ = IntervalSchedule.objects.get_or_create(
        every=2,
        period=IntervalSchedule.MINUTES
    )
    schedule_fetch_logs, _ = IntervalSchedule.objects.get_or_create(
        every=settings.WORKER_FETCH_LOGS_EVERY_SECONDS,
        period=IntervalSchedule.SECONDS
    )

    PeriodicTask.objects.get_or_create(
        interval=schedule_2m,
        name='Update Worker Information',
        task='workers.tasks.update_worker_info',
    )
    PeriodicTask.objects.get_or_create(
        interval=schedule_fetch_logs,
        name='Monitor running workers',
        task='workers.tasks.monitor_workers',
    )
    PeriodicTask.objects.get_or_create(
        interval=schedule_fetch_logs,
        name='Fetch worker analysis logs',
        task='workers.tasks.fetch_running_analysis_logs',
    )


def _parse_deb_list(deb_list_str: str):
    """
    Parse the output of the 'sha256sum *.deb' command to extract package names and their checksums.

    :param deb_list_str: String containing the output of the 'sha256sum *.deb' command
    :return: List of dictionaries with package information
    """
    deb_list = []
    for line in deb_list_str.splitlines():
        try:
            checksum, package_name = line.split('  ')
            deb_info = re.match(r"(?P<name>[^_]+)_(?P<version>[^_]+)_(?P<architecture>[^.]+)\.deb", package_name)
            deb_list.append({
                "name": deb_info.group("name"),
                "version": deb_info.group("version"),
                "architecture": deb_info.group("architecture"),
                "checksum": checksum
            })
        except BaseException as error:
            if line:
                logger.error("Error parsing deb list line '%s': %s", line, error)
            continue
    return deb_list


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
        disk_str = disk_str.splitlines()[0].split()
        disk_total = disk_str[1].replace('G', 'GB').replace('M', 'MB')
        disk_free = disk_str[3].replace('G', 'GB').replace('M', 'MB')
        disk_info = f"Free: {disk_free}  Total: {disk_total}"

        version_regex = r"\d+\.\d+\.\d+[a-z]?"
        emba_version = exec_blocking_ssh(ssh_client, f"sudo cat {os.path.join(settings.WORKER_EMBA_ROOT, 'docker-compose.yml')} | awk -F: '/image:/ {{print $NF; exit}}'")
        emba_version = "N/A" if not re.match(version_regex, emba_version) else emba_version

        commit_regex = r"[0-9a-f]{7,40}"
        last_sync_nvd = exec_blocking_ssh(ssh_client, f"sudo bash -c 'cd {os.path.join(settings.WORKER_EMBA_ROOT, 'external/nvd-json-data-feeds')} && git rev-parse --short HEAD'")
        last_sync_nvd = "N/A" if not re.match(commit_regex, last_sync_nvd) else last_sync_nvd
        last_sync_epss = exec_blocking_ssh(ssh_client, f"sudo bash -c 'cd {os.path.join(settings.WORKER_EMBA_ROOT, 'external/EPSS-data')} && git rev-parse --short HEAD'")
        last_sync_epss = "N/A" if not re.match(commit_regex, last_sync_epss) else last_sync_epss
        last_sync = f"NVD feed: {last_sync_nvd}  EPSS: {last_sync_epss}"

        deb_check = exec_blocking_ssh(ssh_client, "sudo bash -c 'if test -d /root/DEPS/pkg; then echo 'success'; fi'")
        deb_list_str = exec_blocking_ssh(ssh_client, "sudo bash -c 'cd /root/DEPS/pkg && sha256sum *.deb'") if deb_check == 'success' else ""
        deb_list = _parse_deb_list(deb_list_str)

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
        'last_sync': last_sync,
        'deb_list': deb_list
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

            worker.reachable = True
        except paramiko.SSHException:
            logger.info("Worker %s is unreachable, setting status to offline.", worker.name)
            worker.reachable = False
        except BaseException as error:
            logger.error("An error occurred while updating worker %s: %s", worker.name, error)
            continue
        finally:
            worker.save()


@shared_task
def fetch_running_analysis_logs():
    """
    Iterates through the busy workers, zips the analysis log
    files on remote workers, fetches them, extracts them to emba_logs.
    """
    orchestrator = get_orchestrator()
    busy_workers = list(orchestrator.get_busy_workers().values())
    for worker in busy_workers:
        try:
            _fetch_analysis_logs(worker)

        except Exception as exception:
            logger.error("[Worker %s] Unexpected exception: %s", worker.id, exception)


def _fetch_analysis_logs(worker) -> None:
    """
    Zips the analysis log files on remote worker, fetches it, extracts it.

    :param worker: Worker object whose analysis_id logs to process.
    :raises CalledProcessError: If extracting the zipfile fails.
    """
    client = None
    sftp_client = None
    try:
        local_zip_path = f"{settings.MEDIA_ROOT}/log_zip/{worker.analysis_id}.zip"
        local_log_path = f"{settings.EMBA_LOG_ROOT}/{worker.analysis_id}/emba_logs/"

        # SSH and zip the logs
        client = worker.ssh_connect()

        logger.info("[Worker %s] Zipping logs on remote...", worker.id)

        zip_cmd = "cd /root && \
                   7z u -t7z -y emba_logs.zip emba_logs/ -uq3"
        exec_blocking_ssh(client, zip_cmd)

        logger.info("[Worker %s] Zipping logs on remote complete.", worker.id)

        # Ensure log_zip/ exists
        os.makedirs(f"{settings.MEDIA_ROOT}/log_zip/", exist_ok=True)

        # Fetch zip file
        sftp_client = client.open_sftp()
        sftp_client.get("/root/emba_logs.zip", local_zip_path)
        sftp_client.close()
        client.close()

        logger.info("[Worker %s] Downloaded the log zip.", worker.id)

        cmd = ["7z", "x", "-y", local_zip_path, f"-o{local_log_path}"]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)  # nosec

        logger.info("[Worker %s] Finished syncing to to %semba_logs.", worker.id, local_log_path)

    finally:
        if client is not None:
            client.close()


@shared_task
def monitor_workers():
    """
    Periodically checks on the busy workers if the analysis
    is running the Docker conainer and emba.log.

    If the analysis is finished, sets the worker's status
    as free, and performs a soft reset.
    """
    from workers.views import exec_soft_reset_cleanup  # pylint: disable=import-outside-toplevel

    logger.debug("Busy worker health check is running...")

    orchestrator = get_orchestrator()
    busy_workers = list(orchestrator.get_busy_workers().values())
    for worker in busy_workers:
        try:
            is_running = is_emba_container_running(worker)

            analysis = FirmwareAnalysis.objects.get(id=worker.analysis_id)
            if analysis.status["finished"] or not is_running:
                # Fetch logs for the last time
                _fetch_analysis_logs(worker)

                orchestrator.release_worker(worker)

                exec_soft_reset_cleanup(worker)

                logger.info("[Worker %s] Analysis finished.", worker.id)
        except Exception as exception:
            logger.error("[Worker %s] Unexpected exception: %s", worker.id, exception)
            # TODO: Better handle exceptions
            orchestrator.release_worker(worker)
            exec_soft_reset_cleanup(worker)

    logger.debug("Worker health-check complete.")


def is_emba_container_running(worker) -> bool:
    """
    Checks if the Docker container is running on the worker.

    :param worker: The worker to check.
    :return: True, if the Docker container is still running,
             False, otherwise
    """
    try:
        client = worker.ssh_connect()

        cmd = "sudo docker ps -q"
        docker_output = exec_blocking_ssh(client, cmd)
        if docker_output is None:
            logger.info("[Worker %s] EMBA Docker container is no longer running.", worker.id)
            return False

        logger.info("[Worker %s] EMBA Docker container is still running: %s", worker.id, docker_output)
        return True

    except Exception as exception:
        logger.error("[Worker %s] Unexpected exception: %s", worker.id, exception)
        logger.info("[Worker %s] Setting the worker as free.", worker.id)
        return False
    finally:
        client.close()


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
    client.exec_command(f"sudo sh -c '{emba_cmd}' >./terminal.log 2>&1")  # nosec

    future = BoundedExecutor.submit(LogReader, worker.analysis_id)
    if future is None:
        logger.error("start_analysis: Failed to start LogReader.")


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
            config = worker.configurations.first()
            update_system_info(config, worker)
            orchestrator.add_worker(worker)
            logger.info("Worker: %s added to orchestrator", worker.name)
        except ValueError:
            logger.error("Worker: %s already exists in orchestrator", worker.name)
