from typing import Dict, List
from collections import deque
from dataclasses import dataclass

import redis

from workers.models import Worker, OrchestratorInfo


REDIS_CLIENT = redis.Redis()
LOCK_KEY = "orchestrator_lock"
LOCK_TIMEOUT = 60 * 5


@dataclass
class OrchestratorTask:
    firmware_analysis_id: str
    emba_cmd: str
    src_path: str
    target_path: str


class Orchestrator:
    free_workers: Dict[str, Worker] = {}
    busy_workers: Dict[str, Worker] = {}
    tasks = deque()

    def get_busy_workers(self) -> Dict[str, Worker]:
        with REDIS_CLIENT.lock(LOCK_KEY, LOCK_TIMEOUT):
            self._sync_orchestrator_info()
            return self.busy_workers

    def get_free_workers(self) -> Dict[str, Worker]:
        with REDIS_CLIENT.lock(LOCK_KEY, LOCK_TIMEOUT):
            self._sync_orchestrator_info()
            return self.free_workers

    def is_busy(self, worker: Worker) -> bool:
        with REDIS_CLIENT.lock(LOCK_KEY, LOCK_TIMEOUT):
            self._sync_orchestrator_info()
            return worker.ip_address in self.busy_workers

    def get_worker_info(self, worker_ips: List[str]) -> Dict[str, str]:
        """
        Get worker information given a list of worker IPs.

        :param worker_ips: List of worker IP addresses
        :return: Dictionary mapping worker IPs to their job IDs
        :raises ValueError: If a worker IP does not exist in the orchestrator
        """
        with REDIS_CLIENT.lock(LOCK_KEY, LOCK_TIMEOUT):
            self._sync_orchestrator_info()
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

    def _assign_task(self, task: OrchestratorTask):
        """
        Assign a task to a worker. If no workers are free, the task is queued.
        If there are free workers and no tasks in the queue, the task is assigned immediately.
        Otherwise, assigns queued tasks to free workers until no more free workers are available.

        :param task: The task to be assigned
        """
        if not self.free_workers:
            self.tasks.append(task)
        else:
            free_worker = next(iter(self.free_workers.values()))
            if not self.tasks:
                self._assign_worker(free_worker, task)
            else:
                queued_task = self.tasks.popleft()
                self._assign_worker(free_worker, queued_task)
                self._assign_task(task)

    def assign_task(self, task: OrchestratorTask):
        """
        Checks the lock and calls `_assign_task`

        :param task: The task to be assigned
        """
        with REDIS_CLIENT.lock(LOCK_KEY, LOCK_TIMEOUT):
            self._sync_orchestrator_info()
            self._assign_task(task)
            self._update_orchestrator_info()

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
            self._sync_orchestrator_info()
            self._assign_worker(worker, task)
            self._update_orchestrator_info()

    def _release_worker(self, worker: Worker):
        """
        Release a busy worker from its current task. If there are tasks in the queue,
        the next task is assigned to the worker. If no tasks are queued, the worker is marked as free.

        :param worker: The worker to be released
        :raises ValueError: If the worker is not busy
        """
        if worker.ip_address not in self.busy_workers:
            raise ValueError(f"Worker with IP {worker.ip_address} is not busy.")

        if self.tasks:
            next_task = self.tasks.popleft()
            self.free_workers[worker.ip_address] = worker
            del self.busy_workers[worker.ip_address]
            self._assign_worker(worker, next_task)
        else:
            self.free_workers[worker.ip_address] = worker
            del self.busy_workers[worker.ip_address]
            worker.analysis_id = None
            worker.save()

    def release_worker(self, worker: Worker):
        """
        Release a busy worker from its current task. If there are tasks in the queue,
        the next task is assigned to the worker. If no tasks are queued, the worker is marked as free.

        :param worker: The worker to be released
        :raises ValueError: If the worker is not busy
        """
        with REDIS_CLIENT.lock(LOCK_KEY, LOCK_TIMEOUT):
            self._sync_orchestrator_info()
            self._release_worker(worker)
            self._update_orchestrator_info()

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
            self._sync_orchestrator_info()
            self._add_worker(worker)
            self._update_orchestrator_info()

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
            self._sync_orchestrator_info()
            self._remove_worker(worker)
            self._update_orchestrator_info()

    def _get_orchestrator_info(self):
        """ 
        Retrieve the orchestrator info from the database. If it does not exist, create a new one.
        """
        orchestrator_info = OrchestratorInfo.objects.first()
        if not orchestrator_info:
            orchestrator_info = OrchestratorInfo()
            orchestrator_info.save()
        return orchestrator_info
    
    def _sync_orchestrator_info(self):
        """
        Get the latest orchestrator info (free_workers, busy_workers, tasks) from the database and update the internal state.
        """
        orchestrator_info = self._get_orchestrator_info()
        self.free_workers = {worker.ip_address: worker for worker in orchestrator_info.free_workers.all()}
        self.busy_workers = {worker.ip_address: worker for worker in orchestrator_info.busy_workers.all()}
        self.tasks = deque(orchestrator_info.tasks) if orchestrator_info.tasks else deque()

    def _update_orchestrator_info(self):
        """
        Update the orchestrator info in the database with the current state of free_workers, busy_workers, and tasks.
        """
        orchestrator_info = self._get_orchestrator_info()
        orchestrator_info.free_workers.set(self.free_workers.values())
        orchestrator_info.busy_workers.set(self.busy_workers.values())
        orchestrator_info.tasks = list(self.tasks)
        orchestrator_info.save()


orchestrator = Orchestrator()


def get_orchestrator():
    """
    Returns the global singleton instance of the Orchestrator.
    The orchestrator gets started the first time it is accessed.
    """
    return orchestrator
