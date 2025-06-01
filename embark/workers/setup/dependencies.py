import os
import logging
import time

from subprocess import Popen, PIPE
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


def _run_script(script):
    Path(settings.WORKER_FILES_PATH).mkdir(parents=True, exist_ok=True)

    log_file = settings.WORKER_SETUP_LOGS.format(timestamp=int(time.time()))

    logger.info("Worker depenendencies setup started with script %s. Logs: %s", script, log_file)
    try:
        file = os.path.join(os.path.dirname(__file__), script)
        cmd = f"sudo {file} '{settings.WORKER_SETUP_PATH}' '{settings.WORKER_SETUP_ZIP_PATH}'"
        with open(f"{log_file}", "w+", encoding="utf-8") as file:
            with Popen(cmd, stdin=PIPE, stdout=file, stderr=file, shell=True) as proc:  # nosec
                proc.communicate()

            logger.info("Worker depenendencies setup successful. Logs: %s", log_file)
    except BaseException as exception:
        logger.error("Error setting up worker dependencies: %s. Logs: %s", exception, log_file)


def setup_full_dependencies():
    """
    Sets up all dependencies required for offline workers
    """
    setup_deps()
    setup_emba_repo()
    setup_emba_docker_image()
    setup_external_dir()


def setup_emba_repo():
    """
    Sets up the EMBA repo repository
    """
    _run_script("emba_repo_host.sh")


def setup_emba_docker_image():
    """
    Sets up the EMBA docker image to be imported
    """
    _run_script("emba_docker_host.sh")


def setup_external_dir():
    """
    Sets up the external directory
    """
    _run_script("external_host.sh")


def setup_deps():
    """
    Sets up all the required apt dependencies
    """
    _run_script("deps_host.sh")
