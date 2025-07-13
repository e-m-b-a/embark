import logging
import re
import os
import socket

import paramiko
from paramiko.client import SSHClient
from django.conf import settings

from workers.update.dependencies import use_dependency, release_dependency, get_dependency_path, eval_outdated_dependencies
from workers.models import Worker, Configuration, WorkerUpdate, DependencyVersion, DependencyType
from workers.orchestrator import get_orchestrator

logger = logging.getLogger(__name__)


def exec_blocking_ssh(client: SSHClient, command: str):
    """
    Executes ssh command blocking, as exec_command is non-blocking

    Warning: This command might block forever, if the output is too large (based on recv_exit_status). Thus redirect to file

    :params client: modified paramiko ssh client (see: workers.models.Worker.ssh_connect)
    :params command: command string

    :raises SSHException: if command fails

    :return: command output
    """
    stdout = client.exec_command(command)[1]  # nosec B601: No user input

    status = stdout.channel.recv_exit_status()
    if status != 0:
        raise paramiko.ssh_exception.SSHException(f"Command failed with status {status}: {command}")

    return stdout.read().decode().strip()


def _copy_files(client: SSHClient, dependency: DependencyType):
    """
    Copy zipped dependency file to remote

    :params client: paramiko ssh client
    :params dependency: Dependency type
    """
    folder_path = f"/root/{dependency.name}"
    zip_path = f"{folder_path}.tar.gz"
    zip_path_user = zip_path if client.ssh_user == "root" else f"/home/{client.ssh_user}/{dependency.name}.tar.gz"

    exec_blocking_ssh(client, f"sudo rm -f {zip_path}; sudo rm -rf {folder_path}")

    sftp_client = client.open_sftp()
    sftp_client.put(get_dependency_path(dependency)[1], zip_path_user)
    sftp_client.close()

    if client.ssh_user != "root":
        exec_blocking_ssh(client, f"sudo mv {zip_path_user} {zip_path}")


def _get_available_version(dependency: DependencyType) -> str:
    """
    Selects related dependency version of update check
    :param dependency: The dependency to query
    :returns: version string, or "latest" if undefined
    """
    version = DependencyVersion.objects.first()
    if not version:
        version = DependencyVersion()

    match dependency:
        case DependencyType.REPO:
            return version.emba_head
        case DependencyType.DOCKERIMAGE:
            return version.emba
        case DependencyType.DEPS:
            return "cached" if bool(version.deb_list) else "latest"
        case DependencyType.EXTERNAL:
            return version.get_external_version()
        case _:
            raise ValueError("Invalid dependencyType")


def queue_update(worker: Worker, dependency: DependencyType, version=None):
    """
    Adds dependency update to worker update queue
    :param worker: The worker to update
    :param dependency: The dependency to update
    :param version: The desired version of the dependency
    """
    from workers.tasks import update_worker  # pylint: disable=import-outside-toplevel

    if WorkerUpdate.objects.filter(worker__id=worker.id).count() >= settings.WORKER_UPDATE_QUEUE_SIZE:
        logger.info("Update %s discarded for worker %s", dependency.name, worker.name)
        return

    if version is None:
        version = _get_available_version(dependency)

    update = WorkerUpdate(worker=worker, dependency_type=dependency, version=version)
    update.save()

    logger.info("Update %s queued for worker %s", dependency.name, worker.name)

    orchestrator = get_orchestrator()
    if orchestrator.is_busy(worker):
        # Update is performed once the analysis is finished
        return

    if worker.status == Worker.ConfigStatus.CONFIGURING:
        return

    orchestrator.remove_worker(worker, False)

    worker.status = Worker.ConfigStatus.CONFIGURING
    worker.save()

    update_worker.delay(worker.id)


def process_update_queue(worker: Worker):
    """
    Processes the update queue
    :param worker: The worker to update
    """
    if len(WorkerUpdate.objects.filter(worker__id=worker.id)) == 0:
        return

    worker.status = Worker.ConfigStatus.CONFIGURING
    worker.save()

    client = None

    try:
        client = worker.ssh_connect()
        logger.info("Worker update started on worker %s", worker.name)

        while len(updates := WorkerUpdate.objects.filter(worker__id=worker.id)) != 0:
            current_update = updates[0]
            logger.info("Update dependency %s on worker %s", current_update.get_type().name, worker.name)

            perform_update(worker, client, current_update)
            current_update.delete()

        worker.status = Worker.ConfigStatus.CONFIGURED

        logger.info("Worker update finished on worker %s", worker.name)
    except Exception as ssh_error:
        logger.error("SSH connection failed: %s", ssh_error)
        worker.status = Worker.ConfigStatus.ERROR
    finally:
        if client is not None:
            client.close()

        worker.save()
        update_dependencies_info(worker)


def _is_version_installed(worker: Worker, worker_update: WorkerUpdate):
    """
    Checks if desired version is already installed
    :param worker: The worker to update
    :param worker_update: The worker update to apply
    :returns: True if version is already installed
    """
    match worker_update.get_type():
        case DependencyType.REPO:
            return worker.dependency_version.emba_head == worker_update.version
        case DependencyType.DOCKERIMAGE:
            return worker.dependency_version.emba == worker_update.version
        case DependencyType.DEPS:
            return False
        case DependencyType.EXTERNAL:
            return not worker.dependency_version.is_external_outdated(worker_update.version)


def perform_update(worker: Worker, client: SSHClient, worker_update: WorkerUpdate):
    """
    Trigger file copy and installer.sh.
    After an update has been performed, the worker's dependency information is updated.

    :params worker: The worker to update
    :params client: paramiko ssh client
    :params worker_update: The worker update to apply
    """
    dependency = worker_update.get_type()

    if _is_version_installed(worker, worker_update):
        logger.info("Skip update of %s on worker %s as already installed", worker_update.get_type().name, worker.name)
        return

    folder_path = f"/root/{dependency.name}"
    zip_path = f"{folder_path}.tar.gz"

    use_dependency(dependency, worker_update.version, worker)
    _copy_files(client, dependency)
    release_dependency(dependency, worker)

    try:
        exec_blocking_ssh(client, f"sudo rm -rf {folder_path}")
        exec_blocking_ssh(client, f"sudo mkdir {folder_path} && sudo tar xvzf {zip_path} -C {folder_path} >/dev/null 2>&1")
        exec_blocking_ssh(client, f"sudo bash -c '{folder_path}/installer.sh >{folder_path}/installer.log 2>&1'")
    except Exception as ssh_error:
        raise ssh_error

    update_dependencies_info(worker)


def init_sudoers_file(configuration: Configuration, worker: Worker):
    """
    Initializes the sudoers file if it does not exist.
    After this is done, "sudo" can be executed without further password prompts.

    :params configuration: The configuration with user credentials
    :params worker: The worker to edit
    """
    client = None
    sudoers_entry = f"{configuration.ssh_user} ALL=(ALL) NOPASSWD: ALL"
    command = f'sudo -S -p "" bash -c "grep -qxF \'{sudoers_entry}\' /etc/sudoers.d/EMBArk || echo \'{sudoers_entry}\' >> /etc/sudoers.d/EMBArk"'

    try:
        client = worker.ssh_connect()
        stdin, stdout, _ = client.exec_command(command, get_pty=True)  # nosec B601: No user input
        stdin.write(f"{configuration.ssh_password}\n")
        stdin.flush()

        status = stdout.channel.recv_exit_status()
        if status != 0:
            raise paramiko.ssh_exception.SSHException(f"init sudoers file: Command failed with status {status}")

        logger.info("init sudoers file: Added user %s to sudoers of worker %s", configuration.ssh_user, worker.ip_address)
    except Exception as ssh_error:
        logger.error("init sudoers file: Failed. SSH connection failed: %s", ssh_error)
    finally:
        if client is not None:
            client.close()


def update_dependencies_info(worker: Worker):
    """
    Updates dependencies information on worker node
    :param worker: The related worker
    """
    ssh_client = None
    try:
        ssh_client = worker.ssh_connect()

        def _get_head_time(folder):
            commit_regex = r"(latest|[0-9a-f]{40})\s(N\/A|.*\s\+[0-9]{4})"
            path = os.path.join(settings.WORKER_EMBA_ROOT, folder, "git-head-meta")
            meta_info = exec_blocking_ssh(ssh_client, f"sudo bash -c 'if test -f {path}; then cat {path}; fi'")

            match = re.match(commit_regex, meta_info)
            if match:
                return match.group(1), match.group(2) if match.group(2) != "N/A" else None

            return "N/A", None

        docker_compose_path = os.path.join(settings.WORKER_EMBA_ROOT, 'docker-compose.yml')
        emba_version_check = exec_blocking_ssh(ssh_client, f"sudo bash -c 'if test -f {docker_compose_path}; then echo success; fi'")
        worker.dependency_version.emba = exec_blocking_ssh(ssh_client, f"sudo cat {docker_compose_path} | awk -F: '/image:/ {{print $NF; exit}}'") if emba_version_check == 'success' else "N/A"
        worker.dependency_version.emba_head, _ = _get_head_time("")

        worker.dependency_version.nvd_head, worker.dependency_version.nvd_time = _get_head_time("external/nvd-json-data-feeds")
        worker.dependency_version.epss_head, worker.dependency_version.epss_time = _get_head_time("external/EPSS-data")

        deb_check = exec_blocking_ssh(ssh_client, "sudo bash -c 'if test -d /root/DEPS/pkg; then echo 'success'; fi'")
        deb_list_str = exec_blocking_ssh(ssh_client, "sudo bash -c 'cd /root/DEPS/pkg && sha256sum *.deb'") if deb_check == 'success' else ""
        worker.dependency_version.deb_list = parse_deb_list(deb_list_str)
    except (paramiko.SSHException, socket.error) as ssh_error:
        logger.error("SSH connection to worker %s failed: %s", worker.ip_address, ssh_error)
    finally:
        if ssh_client:
            ssh_client.close()

    worker.dependency_version.save()
    logger.info("Dependency info updated for worker %s", worker.ip_address)

    eval_outdated_dependencies(worker)


def parse_deb_list(deb_list_str: str):
    """
    Parse the output of the 'sha256sum *.deb' command to extract package names and their checksums.

    :param deb_list_str: String containing the output of the 'sha256sum *.deb' command
    :return: List of dictionaries with package information
    """
    deb_list = {}
    for line in deb_list_str.splitlines():
        try:
            checksum, package_name = line.split('  ')
            deb_info = re.match(r"(?P<name>[^_]+)_(?P<version>[^_]+)_(?P<architecture>[^.]+)\.deb", package_name)
            deb_list[deb_info.group("name")] = {
                "version": deb_info.group("version"),
                "architecture": deb_info.group("architecture"),
                "checksum": checksum
            }
        except BaseException as error:
            if line:
                logger.error("Error parsing deb list line '%s': %s", line, error)
            continue
    return deb_list
