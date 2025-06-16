from typing import Dict, List
from collections import deque
from threading import Lock

from django.db.models import Q

from workers.models import Worker


class Orchestrator:
    running = False
    tasks = deque()
    free_workers: Dict[str, Worker] = {}
    busy_workers: Dict[str, Worker] = {}
    lock = Lock()

    def start(self):
        """
        Initializes the orchestrator by populating the free and busy workers dictionaries.
        It is assumed that a worker is free if it is configured and has no job assigned,
        and busy if it has a job assigned.
        """
        with self.lock:
            if not self.running:
                self.free_workers = {worker.ip_address: worker for worker in Worker.objects.filter(job_id=None, status=Worker.ConfigStatus.CONFIGURED)}
                self.busy_workers = {worker.ip_address: worker for worker in Worker.objects.filter(~Q(job_id=None), status=Worker.ConfigStatus.CONFIGURED)}
                self.running = True

    def get_busy_workers(self) -> Dict[str, Worker]:
        return self.busy_workers

    def get_free_workers(self) -> Dict[str, Worker]:
        return self.free_workers

    def get_worker_info(self, worker_ips: List[str]) -> Dict[str, str]:
        """
        Get worker information given a list of worker IPs.

        :param worker_ips: List of worker IP addresses
        :return: Dictionary mapping worker IPs to their job IDs
        :raises ValueError: If a worker IP does not exist in the orchestrator
        """
        with self.lock:
            worker_info = {}
            for worker_ip in worker_ips:
                if worker_ip in self.free_workers:
                    worker_info[worker_ip] = "-1"
                elif worker_ip in self.busy_workers:
                    worker = self.busy_workers[worker_ip]
                    worker_info[worker_ip] = f"{worker.job_id}"
                else:
                    raise ValueError(f"Worker with IP {worker_ip} does not exist.")
            return worker_info

    def _assign_task(self, task: str):
        """
        Assign a task to a worker. If no workers are free, the task is queued.
        If there are free workers and no tasks in the queue, the task is assigned immediately.
        Otherwise, assigns queued tasks to free workers until no more free workers are available.

        Note: This function is for internal use only! Call `assign_task` instead

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

    def assign_task(self, task: str):
        """
        Checks the lock and calls `_assign_task`

        :param task: The task to be assigned
        """
        with self.lock:
            self._assign_task(task)

    def _assign_worker(self, worker: Worker, task: str):
        """
        Assign a task to a free worker and mark it as busy.

        Note: This function is for internal use only! Call `assign_worker` instead

        :param worker: The worker to assign the task to
        :param task: The task to be assigned

        :raises ValueError: If the worker is already busy
        """
        if worker.ip_address in self.free_workers:
            worker.job_id = task
            worker.save()
            self.busy_workers[worker.ip_address] = worker
            del self.free_workers[worker.ip_address]
        else:
            raise ValueError(f"Worker with IP {worker.ip_address} is already busy.")

    def assign_worker(self, worker: Worker, task: str):
        """
        Checks the lock and calls `_assign_worker`

        :param worker: The worker to assign the task to
        :param task: The task to be assigned

        :raises ValueError: If the worker is already busy
        """
        with self.lock:
            self._assign_worker(worker, task)

    def release_worker(self, worker: Worker):
        """
        Release a busy worker from its current task. If there are tasks in the queue,
        the next task is assigned to the worker. If no tasks are queued, the worker is marked as free.

        :param worker: The worker to be released

        :raises ValueError: If the worker is not busy
        """
        with self.lock:
            if worker.ip_address in self.busy_workers:
                if self.tasks:
                    next_task = self.tasks.popleft()
                    self.free_workers[worker.ip_address] = worker
                    del self.busy_workers[worker.ip_address]
                    self._assign_worker(worker, next_task)
                else:
                    self.free_workers[worker.ip_address] = worker
                    del self.busy_workers[worker.ip_address]
                    worker.job_id = None
                    worker.save()
            else:
                raise ValueError(f"Worker with IP {worker.ip_address} is not busy.")

    def add_worker(self, worker: Worker):
        """
        Add a new worker to the orchestrator. The worker is added to the free workers list.

        :param worker: The worker to be added

        :raises ValueError: If the worker already exists in the orchestrator
        """
        with self.lock:
            if worker.ip_address not in self.free_workers and worker.ip_address not in self.busy_workers:
                self.free_workers[worker.ip_address] = worker
            else:
                raise ValueError(f"Worker with IP {worker.ip_address} already exists.")

    def remove_worker(self, worker: Worker):
        """
        Remove a worker from the orchestrator.

        :param worker: The worker to be removed

        :raises ValueError: If the worker does not exist in the orchestrator
        """
        with self.lock:
            if worker.ip_address in self.free_workers:
                del self.free_workers[worker.ip_address]
            elif worker.ip_address in self.busy_workers:
                del self.busy_workers[worker.ip_address]
            else:
                raise ValueError(f"Worker with IP {worker.ip_address} does not exist.")


orchestrator = Orchestrator()


def get_orchestrator():
    """
    Returns the global singleton instance of the Orchestrator.
    The orchestrator gets started the first time it is accessed.
    """
    orchestrator.start()
    return orchestrator
