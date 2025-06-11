from typing import Dict
from collections import deque
from workers.models import Worker


class Orchestrator:
    running = False
    tasks = deque()
    free_workers: Dict[str, Worker] = {}
    busy_workers: Dict[str, Worker] = {}

    def start(self):
        """
        Initializes the orchestrator by populating the free and busy workers dictionaries.
        It is assumed that a worker is free if it is configured and has no job assigned,
        and busy if it has a job assigned.
        """
        self.free_workers = {worker.ip_address: worker for worker in Worker.objects.filter(job_id=None, status=Worker.ConfigStatus.CONFIGURED)}
        self.busy_workers = {worker.ip_address: worker for worker in Worker.objects.exclude(job_id=None, status=Worker.ConfigStatus.CONFIGURED)}
        self.running = True

    def get_busy_workers(self) -> Dict[str, Worker]:
        return self.busy_workers

    def get_free_workers(self) -> Dict[str, Worker]:
        return self.free_workers

    def get_worker_info(self, worker_ips) -> Dict[str, str]:
        worker_info = {}
        for worker_ip in worker_ips:
            if worker_ip in self.free_workers:
                worker_info[worker_ip] = "free"
            elif worker_ip in self.busy_workers:
                worker = self.busy_workers[worker_ip]
                worker_info[worker_ip] = f"job: {worker.job_id}"
            else:
                raise ValueError(f"Worker with IP {worker_ip} does not exist.")
        return worker_info

    def assign_task(self, task: str):
        if not self.free_workers:
            self.tasks.append(task)
        else:
            free_worker = next(iter(self.free_workers.values()))
            if not self.tasks:
                self.assign_worker(free_worker, task)
            else:
                queued_task = self.tasks.popleft()
                self.assign_worker(free_worker, queued_task)
                self.assign_task(task)

    def assign_worker(self, worker: Worker, task: str):
        if worker.ip_address in self.free_workers:
            worker.job_id = task
            worker.save()
            self.busy_workers[worker.ip_address] = worker
            del self.free_workers[worker.ip_address]
        else:
            raise ValueError(f"Worker with IP {worker.ip_address} is already busy.")

    def release_worker(self, worker: Worker):
        if worker.ip_address in self.busy_workers:
            if self.tasks:
                next_task = self.tasks.popleft()
                self.free_workers[worker.ip_address] = worker
                del self.busy_workers[worker.ip_address]
                self.assign_worker(worker, next_task)
            else:
                self.free_workers[worker.ip_address] = worker
                del self.busy_workers[worker.ip_address]
                worker.job_id = None
                worker.save()
        else:
            raise ValueError(f"Worker with IP {worker.ip_address} is not busy.")

    def add_worker(self, worker: Worker):
        if worker.ip_address not in self.free_workers and worker.ip_address not in self.busy_workers:
            self.free_workers[worker.ip_address] = worker
        else:
            raise ValueError(f"Worker with IP {worker.ip_address} already exists.")

    def remove_worker(self, worker: Worker):
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
    # TODO: this should probably be made explicit somewhere
    if not orchestrator.running:
        orchestrator.start()
    return orchestrator
