import logging
import re
import os
import socket

import paramiko
from paramiko.client import SSHClient
from django.conf import settings

from workers.update.dependencies import use_dependency, release_dependency, DependencyType, get_dependency_path, eval_outdated_dependencies
from workers.models import Worker, Configuration

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

    # somehow the ssh pw and line endings end up in stdout so we have to remove them
    output = stdout.read().decode().strip()
    output_lines = output.splitlines()
    output_lines = [line for line in output_lines if line.strip() != client.ssh_pw]
    output = "\n".join(output_lines).strip()
    return output


def _copy_files(client: SSHClient, dependency: DependencyType):
    """
    Copy zipped dependency file to remote

    :params client: paramiko ssh client
    :params dependency: Dependency type
    """
    if dependency == DependencyType.ALL:
        raise ValueError("DependencyType.ALL can't be copied")

    folder_path = f"/root/{dependency.name}"
    zip_path = f"{folder_path}.tar.gz"
    zip_path_user = zip_path if client.ssh_user == "root" else f"/home/{client.ssh_user}/{dependency.name}.tar.gz"

    exec_blocking_ssh(client, f"sudo rm -f {zip_path}; sudo rm -rf {folder_path}")

    sftp_client = client.open_sftp()
    sftp_client.put(get_dependency_path(dependency)[1], zip_path_user)
    sftp_client.close()

    if client.ssh_user != "root":
        exec_blocking_ssh(client, f"sudo mv {zip_path_user} {zip_path}")


def perform_update(worker: Worker, client: SSHClient, dependency: DependencyType):
    """
    Trigger file copy and installer.sh

    :params client: paramiko ssh client
    :params dependency: Dependency type
    """
    if dependency == DependencyType.ALL:
        raise ValueError("DependencyType.ALL can't be copied")

    folder_path = f"/root/{dependency.name}"
    zip_path = f"{folder_path}.tar.gz"

    use_dependency(dependency, worker)

    try:
        _copy_files(client, dependency)

        exec_blocking_ssh(client, f"sudo mkdir {folder_path} && sudo tar xvzf {zip_path} -C {folder_path} >/dev/null 2>&1")
        exec_blocking_ssh(client, f"sudo bash -c '{folder_path}/installer.sh >{folder_path}/installer.log 2>&1'")
    except Exception as ssh_error:
        raise ssh_error
    finally:
        release_dependency(dependency, worker)


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
        client = worker.ssh_connect(configuration.id)
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

        docker_compose_path = os.path.join(settings.WORKER_EMBA_ROOT, 'docker-compose.yml')
        emba_version_check = exec_blocking_ssh(ssh_client, f"sudo bash -c 'if test -f {docker_compose_path}; then echo success; fi'")
        worker.dependency_version.emba = exec_blocking_ssh(ssh_client, f"sudo cat {docker_compose_path} | awk -F: '/image:/ {{print $NF; exit}}'") if emba_version_check == 'success' else "N/A"

        def _fetch_external(external_type):
            commit_regex = r".*([0-9a-f]{40})\s(.*\s\+[0-9]{4})"
            path = os.path.join(settings.WORKER_EMBA_ROOT, external_type)
            perform_check = exec_blocking_ssh(ssh_client, f"sudo bash -c 'if test -d {path}; then echo success; fi'")
            if perform_check == 'success':
                result = exec_blocking_ssh(ssh_client, f"sudo bash -c 'cd {path} && git show --no-patch --format=\"%H %ai\" HEAD'")
                match = re.match(commit_regex, result)
                if match:
                    return match.group(1), match.group(2)
            return "N/A", None

        worker.dependency_version.nvd_head, worker.dependency_version.nvd_time = _fetch_external("external/nvd-json-data-feeds")
        worker.dependency_version.epss_head, worker.dependency_version.epss_time = _fetch_external("external/EPSS-data")

        deb_check = exec_blocking_ssh(ssh_client, "sudo bash -c 'if test -d /root/DEPS/pkg; then echo 'success'; fi'")
        deb_list_str = exec_blocking_ssh(ssh_client, "sudo bash -c 'cd /root/DEPS/pkg && sha256sum *.deb'") if deb_check == 'success' else ""
        worker.dependency_version.deb_list = parse_deb_list(deb_list_str)
    except (paramiko.SSHException, socket.error) as ssh_error:
        logger.info("SSH connection to worker %s failed: %s", worker.ip_address, ssh_error)
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
