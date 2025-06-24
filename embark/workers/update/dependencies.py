import os
import time
import logging
from enum import Enum

from subprocess import Popen, PIPE
from pathlib import Path
from threading import Lock

from django.conf import settings
from workers.models import Worker, DependencyVersion

logger = logging.getLogger(__name__)


class DependencyType(Enum):
    """
    Maps dependency type to host script file
    """
    ALL = ""
    DEPS = "deps_host.sh"
    REPO = "emba_repo_host.sh"
    EXTERNAL = "external_host.sh"
    DOCKERIMAGE = "emba_docker_host.sh"


def get_dependency_path(dependency: DependencyType):
    """
    Constructs all relevant paths related to a dependency (folder, zip, done file)

    :params dependency: Dependency type

    :return: folder_path path to folder
    :return: zip_path path to zip
    :return: done_path path to done file (to check if zip generation is actually done)
    """
    if dependency == DependencyType.ALL:
        raise ValueError("DependencyType.ALL can't be copied")

    folder_path = os.path.join(settings.WORKER_FILES_PATH, dependency.name)
    zip_path = folder_path + ".tar.gz"
    done_path = folder_path + ".done"

    return folder_path, zip_path, done_path


class DependencyState:
    """
    Captures full dependency state (mainly used for synchronization)
    """
    class AvailabilityType(Enum):
        UNAVAILABLE = "UNAVAILABLE"
        IN_PROGRESS = "IN_PROGRESS"
        AVAILABLE = "AVAILABLE"

    lock = Lock()
    available = AvailabilityType.UNAVAILABLE
    used_by = []

    def __init__(self, dependency: DependencyType):
        if dependency == DependencyType.ALL:
            raise ValueError("DependencyType.ALL can't be copied")

        done_path = get_dependency_path(dependency)[2]
        self.available = self.AvailabilityType.AVAILABLE if os.path.exists(done_path) else self.AvailabilityType.UNAVAILABLE
        self.dependency = dependency

    def use_dependency(self, worker: Worker):
        """
        Use lock (worker uses dependency)
        If the required files are unavailable, worker setup is delayed and the files are downloaded.
        :params worker: the worker who uses the dependency
        """
        while True:
            with self.lock:
                if self.available == self.AvailabilityType.AVAILABLE:
                    if worker.ip_address in self.used_by:
                        raise ValueError(f"Worker {worker.ip_address} already uses dependency {self.dependency}")

                    self.used_by.append(worker.ip_address)
                    break
                if self.available == self.AvailabilityType.UNAVAILABLE:
                    # Trigger dependency setup (Blocking, as we are already in a celery task)
                    self.available = self.AvailabilityType.IN_PROGRESS
                    setup_dependency(self.dependency)
                    self.available = self.AvailabilityType.AVAILABLE

    def release_dependency(self, worker: Worker, force: bool):
        """
        Releases lock (worker does not use dependency anymore)
        :params worker: the worker who does not use the dependency anymore
        :params force: force release (no error if unused)
        """
        if worker.ip_address not in self.used_by and not force:
            raise ValueError(f"Worker {worker.ip_address} does not use dependency {self.dependency}")

        if worker.ip_address in self.used_by:
            self.used_by.remove(worker.ip_address)

    def is_not_in_use(self):
        """
        Checks if dependency is unused (no worker setup/update is currently performed with this dependency)

        Warning: Assumes thread has the lock
        """
        return len(self.used_by) == 0

    def update_dependency(self, available: bool):
        """
        Sets availability for dependencies
        If the dependency is not setup, the state is UNAVAILABLE.
        If it is currently updated, the state is IN_PROGRESS. Else it is AVAILABLE.

        :params available: true if AVAILABLE, else IN_PROGRESS
        """
        while True:
            with self.lock:
                if self.is_not_in_use():
                    self.available = self.AvailabilityType.AVAILABLE if available else self.AvailabilityType.IN_PROGRESS
                    break

    def uses_dependency(self, worker: Worker):
        """
        Checks if dependency is in use by provided worker
        :params worker: worker to be checked
        :returns: true if dependency is in use
        """
        return worker.ip_address in self.used_by


locks_dict: dict[DependencyType, Lock] = {
    DependencyType.DEPS: DependencyState(DependencyType.DEPS),
    DependencyType.REPO: DependencyState(DependencyType.REPO),
    DependencyType.EXTERNAL: DependencyState(DependencyType.EXTERNAL),
    DependencyType.DOCKERIMAGE: DependencyState(DependencyType.DOCKERIMAGE)
}


def use_dependency(dependency: DependencyType, worker: Worker):
    """
    Use lock (worker uses dependency)
    :params worker: the worker who uses the dependency
    """
    if dependency == DependencyType.ALL:
        raise ValueError("DependencyType.ALL can't be copied")

    locks_dict[dependency].use_dependency(worker)


def release_dependency(dependency: DependencyType, worker: Worker, force=False):
    """
    Releases lock (worker does not use dependency anymore)
    :params dependency: the dependency to release
    :params worker: the worker who does not use the dependency anymore
    :params force: force release (no error if unused)
    """
    if dependency == DependencyType.ALL:
        raise ValueError("DependencyType.ALL can't be copied")

    locks_dict[dependency].release_dependency(worker, force)


def uses_dependency(dependency: DependencyType, worker: Worker):
    """
    Checks if dependency is in use by provided worker
    :params dependency: the dependency to check
    :params worker: worker to be checked
    :returns: true if dependency is in use
    """
    if dependency == DependencyType.ALL:
        raise ValueError("DependencyType.ALL can't be copied")

    return locks_dict[dependency].uses_dependency(worker)


def update_dependency(dependency: DependencyType, available: bool):
    """
    Sets availability for dependencies
    If the dependency is not setup, the state is UNAVAILABLE.
    If it is currently updated, the state is IN_PROGRESS. Else it is AVAILABLE.

    :params dependency: the dependency to check
    :params available: true if AVAILABLE, else IN_PROGRESS
    """
    if dependency == DependencyType.ALL:
        raise ValueError("DependencyType.ALL can't be updated")

    locks_dict[dependency].update_dependency(available)


def eval_outdated_dependencies(worker: Worker):
    """
    Evaluates if dependency version is outdated
    :param worker: The related worker
    """
    version = DependencyVersion.objects.first()
    if not version:
        version = DependencyVersion()

    worker.dependency_version.emba_outdated = version.emba != worker.dependency_version.emba

    worker.dependency_version.external_outdated = version.nvd_head != worker.dependency_version.nvd_head or version.epss_head != worker.dependency_version.epss_head

    # Eval deb list
    deb_list_diff = {
        "new": [],
        "removed": [],
        "updated": [],
    }

    for key, value in worker.dependency_version.deb_list.items():
        if key not in version.deb_list:
            deb_list_diff["removed"].append(key)
            continue

        if value["version"] != version.deb_list[key]["version"]:
            deb_list_diff["updated"].append({
                "name": key,
                "old": value["version"],
                "new": version.deb_list[key]["version"]
            })

    for key in set(version.deb_list.keys()).difference(worker.dependency_version.deb_list.keys()):
        deb_list_diff["new"].append({
            "name": key,
            "new": version.deb_list[key]["version"]
        })

    worker.dependency_version.deb_outdated = bool(deb_list_diff["new"]) or bool(deb_list_diff["removed"]) or bool(deb_list_diff["updated"])
    worker.dependency_version.deb_list_diff = deb_list_diff

    worker.dependency_version.save()
    logger.info("Outdated dependencies evaluated for worker %s", worker.ip_address)


def setup_dependency(dependency):
    """
    Runs script to setup dependency

    :params dependency: Dependency type
    """
    if dependency == DependencyType.ALL:
        raise ValueError("DependencyType.ALL can't be copied")

    Path(settings.WORKER_FILES_PATH).mkdir(parents=True, exist_ok=True)
    Path(os.path.join(settings.WORKER_FILES_PATH, "logs")).mkdir(parents=True, exist_ok=True)

    script_path = os.path.join(os.path.dirname(__file__), dependency.value)
    folder_path, zip_path, done_path = get_dependency_path(dependency)

    # update_dependency(dependency, False)

    log_file = settings.WORKER_SETUP_LOGS.format(timestamp=int(time.time()))

    logger.info("Worker dependencies setup started with script %s. Logs: %s", dependency.value, log_file)
    try:
        cmd = f"sudo {script_path} '{folder_path}' '{zip_path}' '{done_path}'"
        with open(log_file, "w+", encoding="utf-8") as file:
            with Popen(cmd, stdin=PIPE, stdout=file, stderr=file, shell=True) as proc:  # nosec
                proc.communicate()

            logger.info("Worker dependencies setup successful. Logs: %s", log_file)
    except BaseException as exception:
        logger.error("Error setting up worker dependencies: %s. Logs: %s", exception, log_file)

    # update_dependency(dependency, True)
