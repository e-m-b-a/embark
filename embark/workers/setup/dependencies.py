import os
import logging
import time
from enum import Enum

from subprocess import Popen, PIPE
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


class DependencyType(Enum):
    ALL = ""
    DEPS = "deps_host.sh"
    REPO = "emba_repo_host.sh"
    EXTERNAL = "external_host.sh"
    DOCKERIMAGE = "emba_docker_host.sh"


def _run_script(script, folder, update=True):
    """
    Runs script

    :params script: the script to be executed
    :params folder: dependency location
    :params update: if false, aborts if files already present
    """
    Path(settings.WORKER_FILES_PATH).mkdir(parents=True, exist_ok=True)

    script_path = os.path.join(os.path.dirname(__file__), script)
    folder_path = os.path.join(settings.WORKER_FILES_PATH, folder)
    zip_path = folder_path + ".tar.gz"

    if not update and os.path.exists(folder_path) and os.path.exists(zip_path):
        return

    log_file = settings.WORKER_SETUP_LOGS.format(timestamp=int(time.time()))

    logger.info("Worker depenendencies setup started with script %s. Logs: %s", script, log_file)
    try:
        cmd = f"sudo {script_path} '{folder_path}' '{zip_path}'"
        with open(f"{log_file}", "w+", encoding="utf-8") as file:
            with Popen(cmd, stdin=PIPE, stdout=file, stderr=file, shell=True) as proc:  # nosec
                proc.communicate()

            logger.info("Worker depenendencies setup successful. Logs: %s", log_file)
    except BaseException as exception:
        logger.error("Error setting up worker dependencies: %s. Logs: %s", exception, log_file)


def setup_dependencies(dependency_type: DependencyType, update=True):
    """
    Sets up `dependency_type` dependencies required for offline workers
    """
    if dependency_type == DependencyType.ALL:
        _run_script(DependencyType.DEPS.value, DependencyType.DEPS.name, update)
        _run_script(DependencyType.REPO.value, DependencyType.REPO.name, update)
        _run_script(DependencyType.EXTERNAL.value, DependencyType.EXTERNAL.name, update)
        _run_script(DependencyType.DOCKERIMAGE.value, DependencyType.DOCKERIMAGE.name, update)
    else:
        _run_script(dependency_type.value, dependency_type.name, update)
