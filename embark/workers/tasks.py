import socket
import re

import paramiko
from celery import shared_task
from celery.utils.log import get_task_logger

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
def update_worker(worker: Worker, dependency: DependencyType):
    """
    Setup/Update an offline worker and add it to the orchestrator.

    DependencyType.ALL equals a full setup (e.g. new worker), all other DependencyType values are for specific dependencies (e.g. the external directory)

    :params worker: Worker instance
    :params dependency: Dependency type
    """
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
