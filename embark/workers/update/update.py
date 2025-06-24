import logging

import paramiko
from paramiko.client import SSHClient

from workers.models import Worker, Configuration
from workers.update.dependencies import use_dependency, release_dependency, DependencyType, get_dependency_path

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


def undo_sudoers_file(configuration: Configuration, worker: Worker):
    """
    Undos changes from the sudoers file
    After this is done, "sudo" might prompt a password (e.g. if not a root user, not in sudoers file).

    :params configuration: The configuration with user credentials
    :params worker: The worker to edit
    """
    client = None
    sudoers_entry = f"{configuration.ssh_user} ALL=(ALL) NOPASSWD: ALL"
    command = f'sudo bash -c "grep -vxF \'{sudoers_entry}\' /etc/sudoers.d/EMBArk > temp_sudoers; mv -f temp_sudoers /etc/sudoers.d/EMBArk || true"'

    try:
        client = worker.ssh_connect(configuration.id)
        exec_blocking_ssh(client, command)

        logger.info("undo sudoers file: Removed user %s from sudoers of worker %s", configuration.ssh_user, worker.ip_address)
    except Exception as ssh_error:
        logger.error("undo sudoers file: Failed. SSH connection failed: %s", ssh_error)
    finally:
        if client is not None:
            client.close()
