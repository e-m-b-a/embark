import logging

import paramiko
from paramiko.client import SSHClient

from workers.models import Worker
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
    sudo = 'sudo' in command
    command = command.replace('sudo', 'sudo -S -p ""') if sudo else command

    stdin, stdout, _ = client.exec_command(command, get_pty=sudo)  # nosec B601: No user input
    if sudo:
        stdin.write(f"{client.ssh_pw}\n")
        stdin.flush()

    status = stdout.channel.recv_exit_status()
    if status != 0:
        raise paramiko.ssh_exception.SSHException(f"Command failed with status {status}: {command}")

    output = stdout.read().decode().strip()
    # somehow the ssh pw and line endings end up in stdout so we have to remove them
    output = output[len(client.ssh_pw):].strip() if sudo else output
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
