import os
import time
import logging
from enum import Enum

from subprocess import Popen, PIPE
from pathlib import Path
from threading import Lock

from redis import Redis
from django.conf import settings
from workers.models import Worker, DependencyVersion, WorkerUpdate, CachedDependencyVersion

logger = logging.getLogger(__name__)


REDIS_CLIENT = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
LOCK_KEY = "dependency_lock"
LOCK_TIMEOUT = 60 * 5


def get_script_name(dependency: WorkerUpdate.DependencyType):
    script_name = ""
    match dependency:
        case WorkerUpdate.DependencyType.DEPS:
            script_name = "deps"
        case WorkerUpdate.DependencyType.REPO:
            script_name = "emba_repo"
        case WorkerUpdate.DependencyType.EXTERNAL:
            script_name = "external"
        case WorkerUpdate.DependencyType.DOCKERIMAGE:
            script_name = "emba_docker"
        case _:
            raise ValueError("Invalid DependencyType")

    return f"{script_name}_host.sh"


def get_dependency_path(dependency: WorkerUpdate.DependencyType):
    """
    Constructs all relevant paths related to a dependency (folder, zip, done file)

    :params dependency: Dependency type

    :return: folder_path path to folder
    :return: zip_path path to zip
    :return: done_path path to done file (to check if zip generation is actually done)
    """
    folder_path = os.path.join(settings.WORKER_FILES_PATH, dependency.name)
    zip_path = folder_path + ".tar.gz"
    done_path = folder_path + ".done"

    return folder_path, zip_path, done_path


def _is_desired_version_outdated(dependency: WorkerUpdate.DependencyType, desired_version: str):
    """
    Checks if desired version is currently outdated
    :param dependency: The dependency to update
    :param desired_version: the desired version
    :returns: true if desired_version is outdated
    """
    version = CachedDependencyVersion.objects.first()
    if version is None:
        return False

    match dependency:
        case WorkerUpdate.DependencyType.REPO:
            return desired_version in version.emba_head_history
        case WorkerUpdate.DependencyType.DEPS:
            raise ValueError("Deps are never outdated")
        case WorkerUpdate.DependencyType.EXTERNAL:
            return version.is_external_outdated(desired_version)
        case WorkerUpdate.DependencyType.DOCKERIMAGE:
            return desired_version in version.emba_history


def _is_current_version(dependency: WorkerUpdate.DependencyType, desired_version: str):
    """
    Checks if the desired version is currently cached
    :param dependency: The dependency to update
    :param desired_version: the desired version
    :returns: true if desired_version is currently cached
    """
    version = CachedDependencyVersion.objects.first()
    if version is None:
        return False

    match dependency:
        case WorkerUpdate.DependencyType.REPO:
            return version.emba_head == desired_version
        case WorkerUpdate.DependencyType.DEPS:
            return True
        case WorkerUpdate.DependencyType.EXTERNAL:
            return version.get_external_version() == desired_version
        case WorkerUpdate.DependencyType.DOCKERIMAGE:
            return version.emba == desired_version


class DependencyState:
    """
    Captures full dependency state (mainly used for synchronization)
    """
    class AvailabilityType(Enum):
        UNAVAILABLE = "UNAVAILABLE"
        IN_PROGRESS = "IN_PROGRESS"
        AVAILABLE = "AVAILABLE"

    lock = None
    available = AvailabilityType.UNAVAILABLE
    used_by = []

    def __init__(self, dependency: WorkerUpdate.DependencyType):
        done_path = get_dependency_path(dependency)[2]
        self.available = self.AvailabilityType.AVAILABLE if os.path.exists(done_path) else self.AvailabilityType.UNAVAILABLE
        self.dependency = dependency
        self.lock = REDIS_CLIENT.lock(f"{LOCK_KEY}_{dependency.name}", LOCK_TIMEOUT)

    def use_dependency(self, version: str, worker: Worker):
        """
        Use lock (worker uses dependency)
        If the required files are unavailable, worker setup is delayed and the files are downloaded.
        :params version: The version to update to
        :params worker: the worker who uses the dependency
        """
        while True:
            with self.lock:
                if self.available == self.AvailabilityType.AVAILABLE:
                    # If the desired version is outdated, install the cached version as it is newer
                    if _is_current_version(self.dependency, version) or _is_desired_version_outdated(self.dependency, version):
                        if worker.ip_address in self.used_by:
                            raise ValueError(f"Worker {worker.ip_address} already uses dependency {self.dependency}")

                        self.used_by.append(worker.ip_address)
                        break

                    # Else: Trigger dependency setup, as newer version was found
                    self.available = self.AvailabilityType.UNAVAILABLE

                if self.available == self.AvailabilityType.UNAVAILABLE and self.is_not_in_use():
                    # Trigger dependency setup (Blocking, as we are already in a celery task)
                    self.available = self.AvailabilityType.IN_PROGRESS
                    setup_dependency(self.dependency, version)
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


locks_dict: dict[WorkerUpdate.DependencyType, Lock] = {
    WorkerUpdate.DependencyType.DEPS: DependencyState(WorkerUpdate.DependencyType.DEPS),
    WorkerUpdate.DependencyType.REPO: DependencyState(WorkerUpdate.DependencyType.REPO),
    WorkerUpdate.DependencyType.EXTERNAL: DependencyState(WorkerUpdate.DependencyType.EXTERNAL),
    WorkerUpdate.DependencyType.DOCKERIMAGE: DependencyState(WorkerUpdate.DependencyType.DOCKERIMAGE)
}


def use_dependency(dependency: WorkerUpdate.DependencyType, version: str, worker: Worker):
    """
    Use lock (worker uses dependency)
    :params dependency: the dependency to release
    :params version: The version to update to
    :params worker: the worker who uses the dependency
    """
    locks_dict[dependency].use_dependency(version, worker)


def release_dependency(dependency: WorkerUpdate.DependencyType, worker: Worker, force=False):
    """
    Releases lock (worker does not use dependency anymore)
    :params dependency: the dependency to release
    :params worker: the worker who does not use the dependency anymore
    :params force: force release (no error if unused)
    """
    locks_dict[dependency].release_dependency(worker, force)


def uses_dependency(dependency: WorkerUpdate.DependencyType, worker: Worker):
    """
    Checks if dependency is in use by provided worker
    :params dependency: the dependency to check
    :params worker: worker to be checked
    :returns: true if dependency is in use
    """
    return locks_dict[dependency].uses_dependency(worker)


def update_dependency(dependency: WorkerUpdate.DependencyType, available: bool):
    """
    Sets availability for dependencies
    If the dependency is not setup, the state is UNAVAILABLE.
    If it is currently updated, the state is IN_PROGRESS. Else it is AVAILABLE.

    :params dependency: the dependency to check
    :params available: true if AVAILABLE, else IN_PROGRESS
    """
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

    for deb_name, deb_info in worker.dependency_version.deb_list.items():
        if deb_name not in version.deb_list:
            deb_list_diff["removed"].append(deb_name)
            continue

        if deb_info["version"] != version.deb_list[deb_name]["version"]:
            deb_list_diff["updated"].append({
                "name": deb_name,
                "old": deb_info["version"],
                "new": version.deb_list[deb_name]["version"]
            })

    for deb_name in set(version.deb_list.keys()).difference(worker.dependency_version.deb_list.keys()):
        deb_list_diff["new"].append({
            "name": deb_name,
            "new": version.deb_list[deb_name]["version"]
        })

    worker.dependency_version.deb_outdated = bool(deb_list_diff["new"]) or bool(deb_list_diff["removed"]) or bool(deb_list_diff["updated"]) or not bool(worker.dependency_version.deb_list)
    worker.dependency_version.deb_list_diff = deb_list_diff

    worker.dependency_version.save()
    logger.info("Outdated dependencies evaluated for worker %s", worker.ip_address)


def setup_dependency(dependency: WorkerUpdate.DependencyType, version: str):
    """
    Runs script to setup dependency

    :params dependency: Dependency type
    :params version: The desired version
    """
    Path(settings.WORKER_FILES_PATH).mkdir(parents=True, exist_ok=True)
    Path(os.path.join(settings.WORKER_FILES_PATH, "logs")).mkdir(parents=True, exist_ok=True)

    script_path = os.path.join(os.path.dirname(__file__), get_script_name(dependency))
    folder_path, zip_path, done_path = get_dependency_path(dependency)

    log_file = settings.WORKER_SETUP_LOGS.format(timestamp=int(time.time()))

    logger.info("Worker dependencies setup started with script %s. Logs: %s", get_script_name(dependency), log_file)
    try:
        cmd = f"sudo {script_path} '{folder_path}' '{zip_path}' '{done_path}' '{version}'"

        if dependency == WorkerUpdate.DependencyType.DEPS and version == 'cached':
            # Add path, as DEPS are cached here
            cmd = cmd + f" '{settings.WORKER_UPDATE_CHECK}'"

        with open(log_file, "w+", encoding="utf-8") as file:
            with Popen(cmd, stdin=PIPE, stdout=file, stderr=file, shell=True) as proc:  # nosec
                proc.communicate()

            if proc.returncode == 0:
                logger.info("Worker dependencies setup successful. Logs: %s", log_file)
            else:
                logger.error("Worker dependencies setup failed. Logs: %s", log_file)
    except BaseException as exception:
        logger.error("Error setting up worker dependencies: %s. Logs: %s", exception, log_file)

    # Update cached versions
    cached_version = CachedDependencyVersion.objects.first()
    if cached_version is None:
        cached_version = CachedDependencyVersion()

    # Note: APT debs are always updated, thus no version to cache
    match dependency:
        case WorkerUpdate.DependencyType.REPO:
            cached_version.set_emba_head(version)
        case WorkerUpdate.DependencyType.EXTERNAL:
            cached_version.set_external_version(version)
        case WorkerUpdate.DependencyType.DOCKERIMAGE:
            cached_version.set_emba(version)

    cached_version.save()
