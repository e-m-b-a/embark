import os
import logging
import time
import shutil
import re
import subprocess
from enum import Enum

from threading import Lock, Thread
from subprocess import Popen, PIPE
from pathlib import Path

import requests
from django.conf import settings
from workers.models import Worker

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
                    # Trigger dependency setup
                    self.available = self.AvailabilityType.IN_PROGRESS
                    Thread(target=setup_dependency, args=(self.dependency,)).start()

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
    folder_path, zip_path, done_path = get_dependency_path(dependency)

    locks_dict[dependency].update_dependency(False)

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

    locks_dict[dependency].update_dependency(True)


def fetch_dependency_updates():
    """
    Checks if there are updates available
    """
    logger.info("Dependency update check started.")

    # Fetch EMBA + docker image
    response = requests.get("https://raw.githubusercontent.com/e-m-b-a/emba/refs/heads/master/docker-compose.yml", timeout=30)
    match = re.search(r'image:\s?embeddedanalyzer\/emba:(.*?)\n', response.text)
    emba_version = ""
    if match is None:
        logger.error("Update check: EMBA docker-compose.yml does not contain image version")
        emba_version = "ERROR fetching EMBA"
    else:
        emba_version = match.group(1)

    # Fetch external
    def _get_head_time(repo):
        response = requests.get(f"https://api.github.com/repos/EMBA-support-repos/{repo}/commits?per_page=1", timeout=30)
        json_response = response.json()

        return json_response[0]["sha"], json_response[0]["commit"]["author"]["date"]

    nvd_head, nvd_time = _get_head_time("nvd-json-data-feeds")
    epss_head, epss_time = _get_head_time("EPSS-data")

    # Fetch APT
    deb_list = ""
    log_file = settings.WORKER_SETUP_LOGS.format(timestamp=int(time.time()))
    logger.info("APT Dependency update check started. Logs: %s", log_file)
    try:
        script_path = os.path.join(os.path.dirname(__file__), DependencyType.DEPS.value)
        cmd = f"sudo {script_path} '{settings.WORKER_UPDATE_CHECK}' '' ''"
        with open(log_file, "w+", encoding="utf-8") as file:
            with Popen(cmd, stdin=PIPE, stdout=file, stderr=file, shell=True) as proc:  # nosec
                proc.communicate()

            logger.info("APT Dependency update check successful. Logs: %s", log_file)

        deb_list_str = subprocess.check_output(f"cd {os.path.join(settings.WORKER_UPDATE_CHECK, 'pkg')} && sha256sum *.deb", shell=True)  # nosec
        deb_list = parse_deb_list(deb_list_str.decode('utf-8'))
    except BaseException as exception:
        logger.error("Error APT Dependency update check: %s. Logs: %s", exception, log_file)

    shutil.rmtree(settings.WORKER_UPDATE_CHECK, ignore_errors=True)

    # TODO Store in DB
    print(emba_version)
    print(nvd_head)
    print(nvd_time)
    print(epss_head)
    print(epss_time)
    print(deb_list)

    return deb_list


def parse_deb_list(deb_list_str: str):
    """
    Parse the output of the 'sha256sum *.deb' command to extract package names and their checksums.

    :param deb_list_str: String containing the output of the 'sha256sum *.deb' command
    :return: List of dictionaries with package information
    """
    deb_list = []
    for line in deb_list_str.splitlines():
        try:
            checksum, package_name = line.split('  ')
            deb_info = re.match(r"(?P<name>[^_]+)_(?P<version>[^_]+)_(?P<architecture>[^.]+)\.deb", package_name)
            deb_list.append({
                "name": deb_info.group("name"),
                "version": deb_info.group("version"),
                "architecture": deb_info.group("architecture"),
                "checksum": checksum
            })
        except BaseException as error:
            if line:
                logger.error("Error parsing deb list line '%s': %s", line, error)
            continue
    return deb_list
