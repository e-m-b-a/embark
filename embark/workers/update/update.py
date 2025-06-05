import logging

import paramiko
from paramiko.client import SSHClient

from workers.models import Worker
from workers.update.dependencies import use_dependency, release_dependency, DependencyType, get_dependency_path

logger = logging.getLogger(__name__)


def exec_blocking_ssh(client: SSHClient, command):
    """
    Executes ssh command blocking, as exec_command is non-blocking

    Warning: This command might block forever, if the output is too large (based on recv_exit_status). Thus redirect to file

    :params client: paramiko ssh client
    :params command: command string
    """
    _, stdout, _ = client.exec_command(command)  # nosec B601: No user input

    status = stdout.channel.recv_exit_status()
    if status != 0:
        raise paramiko.ssh_exception.SSHException(f"Command failed with status {status}: {command}")


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

    exec_blocking_ssh(client, f"rm -f {zip_path}; rm -rf {folder_path}")

    sftp_client = client.open_sftp()
    sftp_client.put(get_dependency_path(dependency)[1], zip_path)
    sftp_client.close()


def _perform_update(client: SSHClient, dependency: DependencyType):
    """
    Trigger file copy and installer.sh

    :params client: paramiko ssh client
    :params dependency: Dependency type
    """
    if dependency == DependencyType.ALL:
        raise ValueError("DependencyType.ALL can't be copied")

    folder_path = f"/root/{dependency.name}"
    zip_path = f"{folder_path}.tar.gz"

    use_dependency(dependency)

    _copy_files(client, dependency)

    exec_blocking_ssh(client, f"mkdir {folder_path} && tar xvzf {zip_path} -C {folder_path} >/dev/null 2>&1")
    exec_blocking_ssh(client, f"sudo {folder_path}/installer.sh >{folder_path}/installer.log 2>&1")

    release_dependency(dependency)


def update_worker(worker: Worker, dependency: DependencyType):
    """
    Setup/Update an offline worker

    DependencyType.ALL equals a full setup (e.g. new worker), all other DependencyType values are for specific dependencies (e.g. the external directory)

    :params worker: Worker instance
    :params dependency: Dependency type
    """
    logger.info("Worker update started (Dependency: %s)", dependency)

    worker.status = Worker.ConfigStatus.CONFIGURING
    worker.save()

    client = None

    try:
        client = worker.ssh_connect()
        if dependency == DependencyType.ALL:
            _perform_update(client, DependencyType.DEPS)
            _perform_update(client, DependencyType.REPO)
            _perform_update(client, DependencyType.EXTERNAL)
            _perform_update(client, DependencyType.DOCKERIMAGE)
        else:
            _perform_update(client, dependency)

        worker.status = Worker.ConfigStatus.CONFIGURED
        logger.info("Setup done")
    except Exception as ssh_error:
        logger.error("SSH connection failed: %s", ssh_error)
        worker.status = Worker.ConfigStatus.ERROR
    finally:
        if client is not None:
            client.close()
        worker.save()
