__copyright__ = 'Copyright 2025 The AMOS Projects'
__author__ = 'ClProsser, SirGankalot'
__license__ = 'MIT'

import os
import time
import logging

from subprocess import Popen, PIPE
from pathlib import Path

from redis import Redis
from django.conf import settings
from workers.models import Worker, DependencyVersion, DependencyType, CachedDependencyVersion, DependencyState

logger = logging.getLogger(__name__)


REDIS_CLIENT = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
LOCK_KEY = "dependency_lock"


def get_script_name(dependency: DependencyType):
    script_name = ""
    match dependency:
        case DependencyType.DEPS:
            script_name = "deps"
        case DependencyType.REPO:
            script_name = "emba_repo"
        case DependencyType.EXTERNAL:
            script_name = "external"
        case DependencyType.DOCKERIMAGE:
            script_name = "emba_docker"
        case _:
            raise ValueError("Invalid DependencyType")

    return f"{script_name}_host.sh"


def get_dependency_path(dependency: DependencyType):
    """
    Constructs all relevant paths related to a dependency (folder, zip)

    :params dependency: Dependency type

    :return: folder_path path to folder
    :return: zip_path path to zip
    """
    folder_path = os.path.join(settings.WORKER_FILES_PATH, dependency.name)
    zip_path = folder_path + ".tar.gz"

    return folder_path, zip_path


def _is_desired_version_outdated(dependency: DependencyType, desired_version: str):
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
        case DependencyType.REPO:
            return desired_version in version.emba_head_history
        case DependencyType.DEPS:
            raise ValueError("Deps are never outdated")
        case DependencyType.EXTERNAL:
            return version.external_already_installed(desired_version)
        case DependencyType.DOCKERIMAGE:
            return desired_version in version.emba_history


def _is_current_version(dependency: DependencyType, desired_version: str):
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
        case DependencyType.REPO:
            return version.emba_head == desired_version
        case DependencyType.DEPS:
            return True
        case DependencyType.EXTERNAL:
            return version.get_external_version() == desired_version
        case DependencyType.DOCKERIMAGE:
            return version.emba == desired_version


class DependencyLock:
    """
    Captures full dependency state (mainly used for synchronization)
    """
    lock = None

    def __init__(self, dependency: DependencyType):
        self.dependency = dependency
        self.lock = REDIS_CLIENT.lock(f"{LOCK_KEY}_{dependency.name}")

    def _get_db_data(self):
        state, _ = DependencyState.objects.get_or_create(dependency_type=self.dependency)
        return {worker.ip_address: worker for worker in state.used_by.all()}, DependencyState.AvailabilityType(state.availability)

    def _set_db_data(self, used_by=None, availability=None):
        state, _ = DependencyState.objects.get_or_create(dependency_type=self.dependency)
        if used_by is not None:
            state.used_by.set(list(used_by.values()))
        if availability is not None:
            state.availability = availability

        state.save()

    def use_dependency(self, version: str, worker: Worker):
        """
        Use lock (worker uses dependency)
        If the required files are unavailable, worker setup is delayed and the files are downloaded.
        :params version: The version to update to
        :params worker: the worker who uses the dependency
        """
        while True:
            with self.lock:
                used_by, availability = self._get_db_data()
                if availability == DependencyState.AvailabilityType.AVAILABLE:
                    # If the desired version is outdated, install the cached version as it is newer
                    if _is_current_version(self.dependency, version) or _is_desired_version_outdated(self.dependency, version):
                        if worker.ip_address in used_by:
                            raise ValueError(f"Worker {worker.ip_address} already uses dependency {self.dependency}")

                        used_by[worker.ip_address] = worker
                        self._set_db_data(used_by=used_by)
                        worker.write_log(f"\nUsing dependency {self.dependency.name} version {version}\n")
                        break

                    # Else: Trigger dependency setup, as newer version was found
                    self._set_db_data(availability=DependencyState.AvailabilityType.UNAVAILABLE)

                if availability == DependencyState.AvailabilityType.UNAVAILABLE and self.is_not_in_use():
                    # Trigger dependency setup (Blocking, as we are already in a celery task)
                    self._set_db_data(availability=DependencyState.AvailabilityType.IN_PROGRESS)
                    setup_dependency(self.dependency, version)
                    self._set_db_data(availability=DependencyState.AvailabilityType.AVAILABLE)

    def release_dependency(self, worker: Worker, force: bool):
        """
        Releases lock (worker does not use dependency anymore)
        :params worker: the worker who does not use the dependency anymore
        :params force: force release (no error if unused)
        """
        with self.lock:
            used_by, _ = self._get_db_data()

            if worker.ip_address not in used_by and not force:
                raise ValueError(f"Worker {worker.ip_address} does not use dependency {self.dependency}")

            if worker.ip_address in used_by:
                del used_by[worker.ip_address]
                self._set_db_data(used_by=used_by)
                worker.write_log(f"\nReleased dependency {self.dependency.name}\n")

    def is_not_in_use(self):
        """
        Checks if dependency is unused (no worker setup/update is currently performed with this dependency)

        Warning: Assumes thread has the lock
        """
        used_by, _ = self._get_db_data()
        return len(used_by) == 0

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
                    self._set_db_data(availability=DependencyState.AvailabilityType.AVAILABLE if available else DependencyState.AvailabilityType.IN_PROGRESS)
                    break


locks_dict: dict[DependencyType, DependencyLock] = {
    DependencyType.DEPS: DependencyLock(DependencyType.DEPS),
    DependencyType.REPO: DependencyLock(DependencyType.REPO),
    DependencyType.EXTERNAL: DependencyLock(DependencyType.EXTERNAL),
    DependencyType.DOCKERIMAGE: DependencyLock(DependencyType.DOCKERIMAGE)
}


def use_dependency(dependency: DependencyType, version: str, worker: Worker):
    """
    Use lock (worker uses dependency)
    :params dependency: the dependency to release
    :params version: The version to update to
    :params worker: the worker who uses the dependency
    """
    locks_dict[dependency].use_dependency(version, worker)


def release_dependency(dependency: DependencyType, worker: Worker, force=False):
    """
    Releases lock (worker does not use dependency anymore)
    :params dependency: the dependency to release
    :params worker: the worker who does not use the dependency anymore
    :params force: force release (no error if unused)
    """
    locks_dict[dependency].release_dependency(worker, force)


def update_dependency(dependency: DependencyType, available: bool):
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
    worker.write_log(f"\nOutdated dependencies evaluated\n")


def setup_dependency(dependency: DependencyType, version: str):
    """
    Runs script to setup dependency

    :params dependency: Dependency type
    :params version: The desired version
    """
    Path(settings.WORKER_LOG_ROOT).mkdir(parents=True, exist_ok=True)

    script_path = os.path.join(os.path.dirname(__file__), get_script_name(dependency))
    folder_path, zip_path = get_dependency_path(dependency)

    log_file = settings.WORKER_SETUP_LOGS.format(timestamp=int(time.time()))

    logger.info("Worker dependencies setup started with script %s. Logs: %s", get_script_name(dependency), log_file)
    try:
        cmd = ["sudo", script_path, folder_path, zip_path, version]

        if dependency == DependencyType.DEPS and version == 'cached':
            # Add path, as DEPS are cached here
            cmd.append(settings.WORKER_UPDATE_CHECK)

        with open(log_file, "w+", encoding="utf-8") as file:
            with Popen(cmd, stdin=PIPE, stdout=file, stderr=file) as proc:  # nosec
                proc.communicate()

            if proc.returncode == 0:
                logger.info("Worker dependencies setup successful. Logs: %s", log_file)
            else:
                # TODO: The dependency state should not be set to available if the setup failed
                logger.error("Worker dependencies setup failed. Logs: %s", log_file)
    except BaseException as exception:
        logger.error("Error setting up worker dependencies: %s. Logs: %s", exception, log_file)

    # Update cached versions
    cached_version = CachedDependencyVersion.objects.first()
    if cached_version is None:
        cached_version = CachedDependencyVersion()

    # Note: APT debs are always updated, thus no version to cache
    match dependency:
        case DependencyType.REPO:
            cached_version.set_emba_head(version)
        case DependencyType.EXTERNAL:
            cached_version.set_external_version(version)
        case DependencyType.DOCKERIMAGE:
            cached_version.set_emba(version)

    cached_version.save()
