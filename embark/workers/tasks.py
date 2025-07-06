import os
import re
import time
import socket
import subprocess
from pathlib import Path

import requests
import paramiko

from celery import shared_task
from celery.utils.log import get_task_logger
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.conf import settings

from workers.models import Worker, Configuration, DependencyVersion, DependencyType
from workers.update.dependencies import eval_outdated_dependencies, get_script_name, update_dependency, setup_dependency
from workers.update.update import exec_blocking_ssh, parse_deb_list, process_update_queue
from workers.orchestrator import get_orchestrator
from workers.codeql_ignore import new_autoadd_client
from uploader.models import FirmwareAnalysis

logger = get_task_logger(__name__)


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
    exec_blocking_ssh(client, "sudo rm -rf /root/emba_run.log")
    client.exec_command(f"sudo sh -c '{emba_cmd}' >./emba_run.log 2>&1")  # nosec
    logger.info("Firmware analysis has been started on the worker.")

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
    orchestrator = get_orchestrator()
    worker = Worker.objects.get(id=worker_id)
    while True:
        try:
            _fetch_analysis_logs(worker)

            analysis_finished = FirmwareAnalysis.objects.get(id=worker.analysis_id).status["finished"]
            is_running = _is_emba_container_running(worker)

            if not is_running or analysis_finished or not orchestrator.is_busy(worker):
                logger.info("[Worker %s] Analysis finished.", worker.id)
                worker_soft_reset_task(worker.id)
                orchestrator.release_worker(worker)
                orchestrator.trigger()
                process_update_queue(worker)

                if worker.status == Worker.ConfigStatus.CONFIGURED:
                    orchestrator.release_worker(worker)
                else:
                    orchestrator.remove_worker(worker)

                return
        except Exception as exception:
            logger.error("[Worker %s] Unexpected exception: %s", worker.id, exception)
            if orchestrator.is_busy(worker):
                logger.info("[Worker %s] Releasing the worker...", worker.id)
                worker_soft_reset_task(worker.id)
                orchestrator.release_worker(worker)
                orchestrator.trigger()
                return

        time.sleep(15)


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
        zip_cmd = (
            f'sudo bash -c "cd /root && '
            f"7z u -t7z -y {remote_zip_path} {settings.WORKER_EMBA_LOGS} -uq3; "
            f'chown {client.ssh_user}: {remote_zip_path}"'
        )
        exec_blocking_ssh(client, zip_cmd)
        logger.info("[Worker %s] Zipping logs on remote complete.", worker.id)

        # Ensure dirs exists locally
        local_log_dir = f"{settings.EMBA_LOG_ROOT}/{worker.analysis_id}"
        os.makedirs(f"{local_log_dir}/emba_logs/", exist_ok=True)
        os.makedirs(f"{settings.MEDIA_ROOT}/log_zip/", exist_ok=True)

        # Fetch zip file
        local_zip_path = f"{settings.MEDIA_ROOT}/log_zip/{worker.analysis_id}.zip"
        sftp_client = client.open_sftp()
        sftp_client.get(f"{homedir}/emba_logs.zip", local_zip_path)
        logger.info("[Worker %s] Downloaded the log zip.", worker.id)

        # Ensure emba_run.log can be accessed by the user
        if client.ssh_user != "root":
            chown_cmd = f'sudo bash -c "chown {client.ssh_user}: {homedir}/emba_run.log"'
            exec_blocking_ssh(client, chown_cmd)

        sftp_client.get(f"{homedir}/emba_run.log", f"{local_log_dir}/emba_run.log")

        logger.info("[Worker %s] Downloaded emba_run.log.", worker.id)

        unzip_cmd = ["7z", "x", "-y", local_zip_path, f"-o{local_log_dir}/"]
        subprocess.run(unzip_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)  # nosec

        logger.info("[Worker %s] Unzipped the log zip to: %s/emba_logs/", worker.id, local_log_dir)

    finally:
        if sftp_client is not None:
            sftp_client.close()
        if client is not None:
            client.close()


def _is_emba_container_running(worker) -> bool:
    """
    Checks if a Docker container is running on the worker.

    :param worker: The worker to check.
    :return: True, if a Docker container is still running,
             False, otherwise
    """
    client = None
    try:
        client = worker.ssh_connect()

        cmd = "sudo docker ps -qa"
        containers = exec_blocking_ssh(client, cmd)
        if not containers:
            logger.info("[Worker %s] EMBA Docker container is no longer running.", worker.id)
            return False

        return True

    except Exception as exception:
        logger.error("[Worker %s] Unexpected exception: %s", worker.id, exception)
        return False
    finally:
        if client is not None:
            client.close()


@shared_task
def update_worker(worker_id, add_orchestrator=True):
    """
    Setup/Update an offline worker and add it to the orchestrator.

    :params worker_id: The worker to update
    :params add_orchestrator: If True, re-adds worker to orchestrator
    """
    try:
        worker = Worker.objects.get(id=worker_id)
    except Worker.DoesNotExist:
        logger.error("update_worker: Invalid worker id")
        return

    logger.info("update_worker: Worker update task started")

    orchestrator = get_orchestrator()
    try:
        orchestrator.remove_worker(worker)
        orchestrator.trigger()
        logger.info("Worker: %s removed from orchestrator", worker.name)
    except ValueError:
        pass

    process_update_queue(worker)

    if worker.status == Worker.ConfigStatus.CONFIGURED:
        try:
            config = worker.configurations.first()
            update_system_info(config, worker)

            if add_orchestrator:
                orchestrator.add_worker(worker)
                orchestrator.trigger()
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
    Path(settings.WORKER_FILES_PATH).mkdir(parents=True, exist_ok=True)
    Path(os.path.join(settings.WORKER_FILES_PATH, "logs")).mkdir(parents=True, exist_ok=True)

    log_file = settings.WORKER_SETUP_LOGS.format(timestamp=int(time.time()))
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
def worker_soft_reset_task(worker_id, configuration_id=None):
    """
    Connects via SSH to the worker and performs the soft reset
    :param worker_id: ID of worker to soft reset
    :param configuration_id: ID of the configuration based on which the worker needs to be reset
    """
    try:
        worker = Worker.objects.get(id=worker_id)
    except Worker.DoesNotExist:
        logger.error("Worker Soft Reset: Invalid worker id")
        return
    ssh_client = None
    try:
        ssh_client = worker.ssh_connect(configuration_id)
        homedir = "/root" if ssh_client.ssh_user == "root" else f"/home/{ssh_client.ssh_user}"
        exec_blocking_ssh(ssh_client, "sudo docker ps -aq | xargs -r sudo docker stop | xargs -r sudo docker rm || true")
        exec_blocking_ssh(ssh_client, f"sudo rm -rf {settings.WORKER_EMBA_LOGS}")
        exec_blocking_ssh(ssh_client, f"sudo rm -rf {settings.WORKER_FIRMWARE_DIR}")
        exec_blocking_ssh(ssh_client, f"sudo rm -rf {homedir}/emba_logs.zip*")  # Also delete possible leftover tmp files
        exec_blocking_ssh(ssh_client, f"sudo rm -rf {homedir}/emba_run.log")
        ssh_client.close()
    except (paramiko.SSHException, socket.error):
        logger.error("[Worker %s] SSH Connection failed while soft resetting.", worker.id)
        if ssh_client is not None:
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
    command = f"sudo bash -c \"grep -vxF '{sudoers_entry}' /etc/sudoers.d/EMBArk > temp_sudoers; mv -f temp_sudoers /etc/sudoers.d/EMBArk || true\""

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
