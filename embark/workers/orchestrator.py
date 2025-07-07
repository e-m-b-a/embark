__copyright__ = 'Copyright 2025 Siemens Energy AG, Copyright 2025 The AMOS Projects'
__author__ = 'ashiven, ClProsser, SirGankalot'
__license__ = 'MIT'

from uuid import UUID
from typing import Dict, List
from collections import deque
from dataclasses import dataclass

from redis import Redis
from django.conf import settings

from workers.models import Worker, OrchestratorState


REDIS_CLIENT = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
LOCK_KEY = "orchestrator_lock"
LOCK_TIMEOUT = 60 * 5


@dataclass
class OrchestratorTask:
    firmware_analysis_id: UUID
    emba_cmd: str
    src_path: str
    target_path: str

    @classmethod
    def to_dict(cls, task):
        return {
            "firmware_analysis_id": str(task.firmware_analysis_id),
            "emba_cmd": task.emba_cmd,
            "src_path": task.src_path,
            "target_path": task.target_path
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            firmware_analysis_id=UUID(data.get("firmware_analysis_id")),
            emba_cmd=data.get("emba_cmd"),
            src_path=data.get("src_path"),
            target_path=data.get("target_path")
        )


class Orchestrator:
    free_workers: Dict[str, Worker] = {}
    busy_workers: Dict[str, Worker] = {}
    tasks: List[OrchestratorTask] = deque()

    def get_free_workers(self) -> Dict[str, Worker]:
        with REDIS_CLIENT.lock(LOCK_KEY, LOCK_TIMEOUT):
            self._sync_orchestrator_state()
            return self.free_workers

    def _assign_tasks(self):
        """
        Assign tasks to free workers as long as there are both tasks and free workers available.
        """
        if self.tasks and self.free_workers:
            next_task = self.tasks.popleft()
            free_worker = next(iter(self.free_workers.values()))
            self._assign_worker(free_worker, next_task)
            self._assign_tasks()

    def assign_tasks(self):
        """
        Trigger the orchestrator to assign tasks to free workers.
        """
        with REDIS_CLIENT.lock(LOCK_KEY, LOCK_TIMEOUT):
            self._sync_orchestrator_state()
            self._assign_tasks()
            self._update_orchestrator_state()

    def get_busy_workers(self) -> Dict[str, Worker]:
        with REDIS_CLIENT.lock(LOCK_KEY, LOCK_TIMEOUT):
            self._sync_orchestrator_state()
            return self.busy_workers

    def is_free(self, worker: Worker) -> bool:
        with REDIS_CLIENT.lock(LOCK_KEY, LOCK_TIMEOUT):
            self._sync_orchestrator_state()
            return worker.ip_address in self.free_workers

    def is_busy(self, worker: Worker) -> bool:
        with REDIS_CLIENT.lock(LOCK_KEY, LOCK_TIMEOUT):
            self._sync_orchestrator_state()
            return worker.ip_address in self.busy_workers

    def _get_worker_info(self, worker_ips: str) -> Worker:
        """
        Get worker information given a list of worker IPs.

        :param worker_ips: IP address of the worker
        :return: Dictionary mapping worker IPs to their job IDs
        :raises ValueError: If a worker IP does not exist in the orchestrator
        """
        worker_info = {}
        for worker_ip in worker_ips:
            if worker_ip in self.free_workers:
                worker_info[worker_ip] = "-1"
            elif worker_ip in self.busy_workers:
                worker = self.busy_workers[worker_ip]
                worker_info[worker_ip] = f"{worker.analysis_id}"
            else:
                raise ValueError(f"Worker with IP {worker_ip} does not exist.")
        return worker_info

    def get_worker_info(self, worker_ips: List[str]) -> Dict[str, str]:
        """
        Get worker information given a list of worker IPs.

        :param worker_ips: List of worker IP addresses
        :return: Dictionary mapping worker IPs to their job IDs
        :raises ValueError: If a worker IP does not exist in the orchestrator
        """
        with REDIS_CLIENT.lock(LOCK_KEY, LOCK_TIMEOUT):
            self._sync_orchestrator_state()
            return self._get_worker_info(worker_ips)

    def _queue_task(self, task: OrchestratorTask):
        """
        Add a task to the task queue and trigger task assignment.

        :param task: The task to be assigned
        """
        self.tasks.append(task)
        self._assign_tasks()

    def queue_task(self, task: OrchestratorTask):
        """
        Checks the lock and calls `_queue_task`

        :param task: The task to be assigned
        """
        with REDIS_CLIENT.lock(LOCK_KEY, LOCK_TIMEOUT):
            self._sync_orchestrator_state()
            self._queue_task(task)
            self._update_orchestrator_state()

    def _assign_worker(self, worker: Worker, task: OrchestratorTask):
        """
        Assign a task to a free worker and mark it as busy.

        :param worker: The worker to assign the task to
        :param task: The task to be assigned
        :raises ValueError: If the worker is already busy
        """
        # pylint: disable=import-outside-toplevel
        from workers.tasks import start_analysis

        if worker.ip_address in self.free_workers:
            worker.analysis_id = task.firmware_analysis_id
            worker.save()

            start_analysis.delay(worker.id, task.emba_cmd, task.src_path, task.target_path)

            self.busy_workers[worker.ip_address] = worker
            del self.free_workers[worker.ip_address]
        else:
            raise ValueError(f"Worker with IP {worker.ip_address} is already busy.")

    def assign_worker(self, worker: Worker, task: OrchestratorTask):
        """
        Checks the lock and calls `_assign_worker`

        :param worker: The worker to assign the task to
        :param task: The task to be assigned
        :raises ValueError: If the worker is already busy
        """
        with REDIS_CLIENT.lock(LOCK_KEY, LOCK_TIMEOUT):
            self._sync_orchestrator_state()
            self._assign_worker(worker, task)
            self._update_orchestrator_state()

    def _release_worker(self, worker: Worker):
        """
        Release a busy worker from its current task.

        :param worker: The worker to be released
        :raises ValueError: If the worker is not busy
        """
        if worker.ip_address not in self.busy_workers:
            raise ValueError(f"Worker with IP {worker.ip_address} is not busy.")

        self.free_workers[worker.ip_address] = worker
        del self.busy_workers[worker.ip_address]
        worker.analysis_id = None
        worker.save()

    def release_worker(self, worker: Worker):
        """
        Release a busy worker from its current task and mark it as free.

        :param worker: The worker to be released
        :raises ValueError: If the worker is not busy
        """
        with REDIS_CLIENT.lock(LOCK_KEY, LOCK_TIMEOUT):
            self._sync_orchestrator_state()
            self._release_worker(worker)
            self._update_orchestrator_state()

    def _add_worker(self, worker: Worker):
        """
        Add a new worker to the orchestrator. The worker is added to the free workers list.

        :param worker: The worker to be added
        :raises ValueError: If the worker already exists in the orchestrator
        """
        if worker.ip_address in self.free_workers or worker.ip_address in self.busy_workers:
            raise ValueError(f"Worker with IP {worker.ip_address} already exists.")
        self.free_workers[worker.ip_address] = worker

    def add_worker(self, worker: Worker):
        """
        Add a new worker to the orchestrator. The worker is added to the free workers list.

        :param worker: The worker to be added
        :raises ValueError: If the worker already exists in the orchestrator
        """
        with REDIS_CLIENT.lock(LOCK_KEY, LOCK_TIMEOUT):
            self._sync_orchestrator_state()
            self._add_worker(worker)
            self._update_orchestrator_state()

    def _remove_worker(self, worker: Worker):
        """
        Remove a worker from the orchestrator. The worker is removed from either the free or busy workers list.

        :param worker: The worker to be removed
        :raises ValueError: If the worker does not exist in the orchestrator
        """
        if worker.ip_address in self.free_workers:
            del self.free_workers[worker.ip_address]
        elif worker.ip_address in self.busy_workers:
            del self.busy_workers[worker.ip_address]
        else:
            raise ValueError(f"Worker with IP {worker.ip_address} does not exist.")

    def remove_worker(self, worker: Worker):
        """
        Remove a worker from the orchestrator.

        :param worker: The worker to be removed
        :raises ValueError: If the worker does not exist in the orchestrator
        """
        with REDIS_CLIENT.lock(LOCK_KEY, LOCK_TIMEOUT):
            self._sync_orchestrator_state()
            self._remove_worker(worker)
            self._update_orchestrator_state()

    def _get_orchestrator_state(self):
        """
        Retrieve the orchestrator state from the database. If it does not exist, create a new one.
        """
        orchestrator_state = OrchestratorState.objects.first()
        if not orchestrator_state:
            orchestrator_state = OrchestratorState()
            orchestrator_state.save()
        return orchestrator_state

    def _sync_orchestrator_state(self):
        """
        Get the latest orchestrator state (free_workers, busy_workers, tasks) from the database and update the internal state.
        """
        orchestrator_state = self._get_orchestrator_state()
        self.free_workers = {worker.ip_address: worker for worker in orchestrator_state.free_workers.all()}
        self.busy_workers = {worker.ip_address: worker for worker in orchestrator_state.busy_workers.all()}
        self.tasks = deque([OrchestratorTask.from_dict(task) for task in orchestrator_state.tasks]) if orchestrator_state.tasks else deque()

    def _update_orchestrator_state(self):
        """
        Update the orchestrator state in the database with the internal state of free_workers, busy_workers, and tasks.
        """
        orchestrator_state = self._get_orchestrator_state()
        orchestrator_state.free_workers.set(list(self.free_workers.values()))
        orchestrator_state.busy_workers.set(list(self.busy_workers.values()))
        orchestrator_state.tasks = [OrchestratorTask.to_dict(task) for task in self.tasks]
        orchestrator_state.save()


orchestrator = Orchestrator()


def get_orchestrator():
    """
    Returns the global singleton instance of the Orchestrator.
    The orchestrator gets started the first time it is accessed.
    """
    return orchestrator
