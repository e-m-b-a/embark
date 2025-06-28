import socket
import re
import os
import shutil
import subprocess
import time

import paramiko
from celery import shared_task
from celery.utils.log import get_task_logger

import requests
from django.conf import settings

from workers.models import Worker, Configuration, DependencyVersion, WorkerUpdate
from workers.update.dependencies import eval_outdated_dependencies, get_script_name
from workers.update.update import exec_blocking_ssh, perform_update, update_dependencies_info, parse_deb_list
from workers.orchestrator import get_orchestrator
from workers.codeql_ignore import new_autoadd_client

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
        disk_str = disk_str.splitlines()[0].split()
        disk_total = disk_str[1].replace('G', 'GB').replace('M', 'MB')
        disk_free = disk_str[3].replace('G', 'GB').replace('M', 'MB')
        disk_info = f"Free: {disk_free}  Total: {disk_total}"

        ssh_client.close()

    except (paramiko.SSHException, socket.error) as ssh_error:
        if ssh_client:
            ssh_client.close()
        raise paramiko.SSHException("SSH connection failed") from ssh_error

    system_info = {
        'os_info': os_info,
        'cpu_info': cpu_info,
        'ram_info': ram_info,
        'disk_info': disk_info
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
def update_worker(worker_id):
    """
    Setup/Update an offline worker and add it to the orchestrator.

    :params worker_id: The worker to update
    """
    try:
        worker = Worker.objects.get(id=worker_id)
    except Worker.DoesNotExist:
        logger.error("start_analysis: Invalid worker id")
        return

    logger.info("Worker update started")

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

        while len(updates := WorkerUpdate.objects.filter(worker__id=worker.id)) != 0:
            current_update = updates[0]
            perform_update(worker, client, current_update)
            current_update.delete()

        worker.status = Worker.ConfigStatus.CONFIGURED
        worker.save()

        update_dependencies_info(worker)
        logger.info("Worker update finished")
    except Exception as ssh_error:
        logger.error("SSH connection failed: %s", ssh_error)
        worker.status = Worker.ConfigStatus.ERROR
    finally:
        if client is not None:
            client.close()

    if worker.status == Worker.ConfigStatus.CONFIGURED:
        try:
            config = worker.configurations.first()
            update_system_info(config, worker)
            orchestrator.add_worker(worker)
            logger.info("Worker: %s added to orchestrator", worker.name)
        except ValueError:
            logger.error("Worker: %s already exists in orchestrator", worker.name)


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
    EXTERNAL_URL = "https://api.github.com/repos/EMBA-support-repos/{}/commits?per_page=1"  # pylint: disable=invalid-name

    # Fetch EMBA + docker image
    try:
        response = requests.get(DOCKER_COMPOSE_URL, timeout=30)
        match = re.search(r'image:\s?embeddedanalyzer\/emba:(.*?)\n', response.text)

        if match is None:
            logger.error("Update check: Failed. EMBA docker-compose.yml does not contain image version")
            version.emba = "ERROR fetching EMBA"
        else:
            version.emba = match.group(1)
    except requests.exceptions.Timeout as exception:
        logger.error("Update check: Failed. An error occured on contacting GH API for docker-compose.yml: %s", exception)

    # Fetch external
    def _get_head_time(repo):
        try:
            response = requests.get(EXTERNAL_URL.format(repo), timeout=30)
            json_response = response.json()

            return json_response[0]["sha"], json_response[0]["commit"]["author"]["date"]
        except requests.exceptions.Timeout as exception:
            logger.error("Update check: Failed. An error occured on contacting GH API: %s", exception)
        except (requests.exceptions.JSONDecodeError, KeyError):
            logger.error("Update check: Failed. GH API returned invalid or incomplete json: %s", response.text)
        return "N/A", None

    version.nvd_head, version.nvd_time = _get_head_time("nvd-json-data-feeds")
    version.epss_head, version.epss_time = _get_head_time("EPSS-data")

    # Fetch APT
    log_file = settings.WORKER_SETUP_LOGS.format(timestamp=int(time.time()))
    logger.info("APT dependency update check started. Logs: %s", log_file)
    try:
        script_path = os.path.join(os.path.dirname(__file__), "update", get_script_name(WorkerUpdate.DependencyType.DEPS))
        cmd = f"sudo {script_path} '{settings.WORKER_UPDATE_CHECK}' '' ''"
        with open(log_file, "w+", encoding="utf-8") as file:
            with subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=file, stderr=file, shell=True) as proc:  # nosec
                proc.communicate()

            logger.info("APT dependency update check successful. Logs: %s", log_file)

        deb_list_str = subprocess.check_output(f"cd {os.path.join(settings.WORKER_UPDATE_CHECK, 'pkg')} && sha256sum *.deb", shell=True)  # nosec
        version.deb_list = parse_deb_list(deb_list_str.decode('utf-8'))
    except BaseException as exception:
        logger.error("Error APT dependency update check: %s. Logs: %s", exception, log_file)
        version.deb_list = {}

    shutil.rmtree(settings.WORKER_UPDATE_CHECK, ignore_errors=True)

    # Store in DB
    version.save()

    # Evaluate for each worker
    workers = Worker.objects.all()
    for worker in workers:
        eval_outdated_dependencies(worker)


@shared_task
def worker_soft_reset_task(worker_id, configuration_id):
    try:
        worker = Worker.objects.get(id=worker_id)
    except Worker.DoesNotExist:
        logger.error("Worker Soft Reset: Invalid worker id")
        return
    ssh_client = None
    try:
        ssh_client = worker.ssh_connect(configuration_id)
        exec_blocking_ssh(ssh_client, "sudo docker ps -aq | xargs -r sudo docker stop | xargs -r sudo docker rm || true")
        exec_blocking_ssh(ssh_client, f"sudo rm -rf {settings.WORKER_EMBA_LOGS}")
        exec_blocking_ssh(ssh_client, f"sudo rm -rf {settings.WORKER_FIRMWARE_DIR}")
        ssh_client.close()
    except (paramiko.SSHException, socket.error):
        logger.error("SSH Connection didnt work for: %s", worker.name)
        if ssh_client:
            ssh_client.close()


@shared_task
def worker_hard_reset_task(worker_id, configuration_id):
    try:
        worker = Worker.objects.get(id=worker_id)
    except Worker.DoesNotExist:
        logger.error("Worker Hard Reset: Invalid worker id")
        return
    ssh_client = None
    try:
        ssh_client = worker.ssh_connect(configuration_id)
        emba_path = os.path.join(settings.WORKER_EMBA_ROOT, "full_uninstaller.sh")
        exec_blocking_ssh(ssh_client, "sudo bash " + emba_path)
        ssh_client.close()
    except (paramiko.SSHException, socket.error):
        logger.error("SSH Connection didnt work for: %s", worker.name)
        if ssh_client:
            ssh_client.close()


@shared_task
def undo_sudoers_file(ip_address, ssh_user, ssh_password):
    """
    Undos changes from the sudoers file
    After this is done, "sudo" might prompt a password (e.g. if not a root user, not in sudoers file).
    Note: Once this task is called, the configuration is already deleted (and the worker might too)

    Note: If two configurations with the same username exist, the entry in the sudoers file is removed (while it might still be needed).

    :params ip_address: The worker ip address
    :params ssh_user: The worker ssh_user
    :params ssh_password: The worker ssh_password
    """
    client = None
    sudoers_entry = f"{ssh_user} ALL=(ALL) NOPASSWD: ALL"
    command = f'sudo bash -c "grep -vxF \'{sudoers_entry}\' /etc/sudoers.d/EMBArk > temp_sudoers; mv -f temp_sudoers /etc/sudoers.d/EMBArk || true"'

    try:
        client = new_autoadd_client()
        client.connect(ip_address, username=ssh_user, password=ssh_password)
        exec_blocking_ssh(client, command)

        logger.info("undo sudoers file: Removed user %s from sudoers of worker %s", ssh_user, ip_address)
    except Exception as ssh_error:
        logger.error("undo sudoers file: Failed. SSH connection failed: %s", ssh_error)
    finally:
        if client is not None:
            client.close()
