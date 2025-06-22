import socket
import re
import os

import paramiko
from celery import shared_task
from celery.utils.log import get_task_logger

from django.conf import settings

from workers.models import Worker, Configuration
from workers.update.dependencies import DependencyType
from workers.update.update import exec_blocking_ssh, perform_update
from workers.orchestrator import get_orchestrator

logger = get_task_logger(__name__)


def create_periodic_tasks(**kwargs):
    """
    Create periodic tasks with the start of the application. (called in ready() method of the app config)
    """
    from django_celery_beat.models import PeriodicTask, IntervalSchedule  # pylint: disable=import-outside-toplevel
    schedule, _created = IntervalSchedule.objects.get_or_create(
        every=2,
        period=IntervalSchedule.MINUTES
    )
    PeriodicTask.objects.get_or_create(
        interval=schedule,
        name='Update Worker Information',
        task='workers.tasks.update_worker_info',
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

        emba_version_check = exec_blocking_ssh(ssh_client, f"sudo bash -c 'if test -f {os.path.join(settings.WORKER_EMBA_ROOT, 'docker-compose.yml')}; then echo success; fi'")
        emba_version = exec_blocking_ssh(ssh_client, f"sudo cat {os.path.join(settings.WORKER_EMBA_ROOT, 'docker-compose.yml')} | awk -F: '/image:/ {{print $NF; exit}}'") if emba_version_check == 'success' else "N/A"

        last_sync_nvd_check = exec_blocking_ssh(ssh_client, f"sudo bash -c 'if test -d {os.path.join(settings.WORKER_EMBA_ROOT, 'external/nvd-json-data-feeds')}; then echo success; fi'")
        last_sync_nvd = exec_blocking_ssh(ssh_client, f"sudo bash -c 'cd {os.path.join(settings.WORKER_EMBA_ROOT, 'external/nvd-json-data-feeds')} && git rev-parse --short HEAD'") if last_sync_nvd_check == 'success' else "N/A"
        last_sync_epss_check = exec_blocking_ssh(ssh_client, f"sudo bash -c 'if test -d {os.path.join(settings.WORKER_EMBA_ROOT, 'external/EPSS-data')}; then echo success; fi'")
        last_sync_epss = exec_blocking_ssh(ssh_client, f"sudo bash -c 'cd {os.path.join(settings.WORKER_EMBA_ROOT, 'external/EPSS-data')} && git rev-parse --short HEAD'") if last_sync_epss_check == 'success' else "N/A"
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
            config = worker.configurations.first()
            update_system_info(config, worker)
            orchestrator.add_worker(worker)
            logger.info("Worker: %s added to orchestrator", worker.name)
        except ValueError:
            logger.error("Worker: %s already exists in orchestrator", worker.name)
