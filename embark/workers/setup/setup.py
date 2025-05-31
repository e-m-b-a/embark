import logging

import paramiko

from django.conf import settings

from workers.models import Worker
from workers.setup.dependencies import setup_full_dependencies

logger = logging.getLogger(__name__)


def exec_blocking_ssh(client, command):
    """
    Executes ssh command blocking, as exec_command is non-blocking

    Warning: This command might block forever, if the output is too large (based on recv_exit_status)

    :params client: paramiko ssh client
    :params command: command string
    """
    _, stdout, _ = client.exec_command(command)  # nosec B601: No user input

    status = stdout.channel.recv_exit_status()
    if status != 0:
        raise paramiko.SSHException(f"Command failed with status {status}: {command}")


def setup_worker(worker: Worker):
    """
    Transfers dependencies to offline worker and executes script

    :params worker: Worker instance
    """
    # TODO: Move to better place (e.g. if workers are enabled in config)
    setup_full_dependencies()

    logger.info("Setup started")

    worker.status = Worker.ConfigStatus.CONFIGURING
    worker.save()

    ssh_client = worker.ssh_connect()

    try:
        sftp_client = ssh_client.open_sftp()
        sftp_client.put(settings.WORKER_SETUP_ZIP_PATH, "/root/WORKER_SETUP.tar.gz")
        sftp_client.close()

        exec_blocking_ssh(ssh_client, 'tar xvzf /root/WORKER_SETUP.tar.gz >untar.log 2>&1')
        exec_blocking_ssh(ssh_client, 'sudo /root/WORKER_SETUP/installer.sh >installer.log 2>&1')

        worker.status = Worker.ConfigStatus.CONFIGURED
        logger.info("Setup done")
    except paramiko.SSHException as ssh_error:
        logger.error("SSH connection failed: %s", ssh_error)
        worker.status = Worker.ConfigStatus.ERROR
    finally:
        ssh_client.close()
        worker.save()
