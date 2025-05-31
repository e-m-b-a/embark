import os
import logging

from subprocess import Popen, PIPE
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


def setup_full_dependencies():
    """
    Sets up all dependencies required for offline workers
    """
    Path(settings.WORKER_FILES_PATH).mkdir(parents=True, exist_ok=True)

    if not os.path.isdir(settings.WORKER_SETUP_PATH) or not os.path.exists(settings.WORKER_SETUP_ZIP_PATH):
        try:
            file = os.path.join(os.path.dirname(__file__), "host.sh")
            cmd = f"sudo {file} '{settings.WORKER_SETUP_PATH}' '{settings.WORKER_SETUP_ZIP_PATH}'"
            with open(f"{settings.WORKER_SETUP_LOGS}", "w+", encoding="utf-8") as file:
                with Popen(cmd, stdin=PIPE, stdout=file, stderr=file, shell=True) as proc:  # nosec
                    proc.communicate()

                logger.info("Worker depenendencies setup successful")
        except BaseException as exception:
            logger.error("Error setting up worker dependencies: %s", exception)


def setup_emba_repo():
    return


def setup_emba_docker_image():
    return


def setup_external_dir():
    return
