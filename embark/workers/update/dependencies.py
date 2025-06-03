import os
import logging
import time
from enum import Enum

from threading import Lock, Thread
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


def get_dependency_path(dependency: DependencyType):
    if dependency == DependencyType.ALL:
        raise ValueError("DependencyType.ALL can't be copied")

    return os.path.join(settings.WORKER_FILES_PATH, dependency.name)


def get_dependency_zip_path(dependency: DependencyType):
    if dependency == DependencyType.ALL:
        raise ValueError("DependencyType.ALL can't be copied")

    return get_dependency_path(dependency) + ".tar.gz"


class DependencyState:
    class AvailabilityType(Enum):
        UNAVAILABLE = "UNAVAILABLE"
        IN_PROGRESS = "IN_PROGRESS"
        AVAILABLE = "AVAILABLE"

    lock = Lock()
    available = AvailabilityType.UNAVAILABLE
    in_use = 0  # n times currently used to setup offline workers

    def __init__(self, dependency: DependencyType):
        if dependency == DependencyType.ALL:
            raise ValueError("DependencyType.ALL can't be copied")

        self.available = self.AvailabilityType.UNAVAILABLE  # TODO
        self.dependency = dependency

    def use_dependency(self):
        while True:
            with self.lock:
                if self.available == self.AvailabilityType.AVAILABLE:
                    self.in_use = self.in_use + 1
                    break
                if self.available == self.AvailabilityType.UNAVAILABLE:
                    # Trigger update
                    self.available = self.AvailabilityType.IN_PROGRESS
                    Thread(target=setup_dependency, args=(self.dependency,)).start()

    def release_dependency(self):
        with self.lock:
            self.in_use = self.in_use - 1

    def is_not_in_use(self):
        return self.in_use == 0

    def update_dependency(self, available: bool):
        while True:
            with self.lock:
                if self.is_not_in_use():
                    self.available = self.AvailabilityType.AVAILABLE if available else self.AvailabilityType.IN_PROGRESS
                    break


locks_dict: dict[DependencyType, Lock] = {
    DependencyType.DEPS: DependencyState(DependencyType.DEPS),
    DependencyType.REPO: DependencyState(DependencyType.REPO),
    DependencyType.EXTERNAL: DependencyState(DependencyType.EXTERNAL),
    DependencyType.DOCKERIMAGE: DependencyState(DependencyType.DOCKERIMAGE)
}


def use_dependency(dependency: DependencyType):
    if dependency == DependencyType.ALL:
        raise ValueError("DependencyType.ALL can't be copied")

    locks_dict[dependency].use_dependency()


def release_dependency(dependency: DependencyType):
    if dependency == DependencyType.ALL:
        raise ValueError("DependencyType.ALL can't be copied")

    locks_dict[dependency].release_dependency()


def setup_dependency(dependency: DependencyType):
    """
    Runs script to setup dependency

    :params dependency: Dependency type
    """
    if dependency == DependencyType.ALL:
        raise ValueError("DependencyType.ALL can't be copied")

    Path(settings.WORKER_FILES_PATH).mkdir(parents=True, exist_ok=True)
    Path(os.path.join(settings.WORKER_FILES_PATH, "logs")).mkdir(parents=True, exist_ok=True)

    script_path = os.path.join(os.path.dirname(__file__), dependency.value)
    folder_path = get_dependency_path(dependency)
    zip_path = get_dependency_zip_path(dependency)

    locks_dict[dependency].update_dependency(False)

    log_file = settings.WORKER_SETUP_LOGS.format(timestamp=int(time.time()))

    logger.info("Worker dependencies setup started with script %s. Logs: %s", dependency.value, log_file)
    try:
        cmd = f"sudo {script_path} '{folder_path}' '{zip_path}'"
        with open(f"{log_file}", "w+", encoding="utf-8") as file:
            with Popen(cmd, stdin=PIPE, stdout=file, stderr=file, shell=True) as proc:  # nosec
                proc.communicate()

            logger.info("Worker dependencies setup successful. Logs: %s", log_file)
    except BaseException as exception:
        logger.error("Error setting up worker dependencies: %s. Logs: %s", exception, log_file)

    locks_dict[dependency].update_dependency(True)
