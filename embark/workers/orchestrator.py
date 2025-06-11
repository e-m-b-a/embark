from typing import Dict
from collections import deque
from workers.models import Worker


class WorkerOrchestrator:
    queue_tasks = deque()
    dict_free_workers: Dict[str, Worker] = {}
    dict_busy_workers: Dict[str, Worker] = {}

    def start(self):
        self.dict_free_workers = {worker.ip_address: worker for worker in Worker.objects.filter(job_id=None)}
        self.dict_busy_workers = {worker.ip_address: worker for worker in Worker.objects.exclude(job_id=None)}

    def get_busy_workers(self) -> Dict[str, Worker]:
        return self.dict_busy_workers

    def get_free_workers(self) -> Dict[str, Worker]:
        return self.dict_free_workers

    def get_specific_workers(self, worker_ips) -> Worker:
        map_worker_array = {}
        for worker_ip in worker_ips:
            if worker_ip in self.dict_free_workers:
                map_worker_array[worker_ip] = "free"
            elif worker_ip in self.dict_busy_workers:
                worker = self.dict_busy_workers[worker_ip]
                map_worker_array[worker_ip] = f"job: {worker.job_id}"
            else:
                raise ValueError(f"Worker with IP {worker_ip} does not exist.")
        return map_worker_array

    def assign_task(self, task: str):
        if not self.dict_free_workers:
            self.queue_tasks.append(task)
        else:
            free_worker = next(iter(self.dict_free_workers.values()))
            if not self.queue_tasks:
                self.assign_worker(free_worker, task)
            else:
                queued_task = self.queue_tasks.popleft()
                self.assign_worker(free_worker, queued_task)
                self.assign_task(task)

    def assign_worker(self, worker: Worker, task: str):
        if worker.ip_address in self.dict_free_workers:
            worker.job_id = task
            worker.save()
            self.dict_busy_workers[worker.ip_address] = worker
            del self.dict_free_workers[worker.ip_address]
        else:
            raise ValueError(f"Worker with IP {worker.ip_address} is already busy.")

    def release_worker(self, worker: Worker):
        if worker.ip_address in self.dict_busy_workers:
            if self.queue_tasks:
                next_task = self.queue_tasks.popleft()
                self.dict_free_workers[worker.ip_address] = worker
                del self.dict_busy_workers[worker.ip_address]
                self.assign_worker(worker, next_task)
            else:
                self.dict_free_workers[worker.ip_address] = worker
                del self.dict_busy_workers[worker.ip_address]
                worker.job_id = None
                worker.save()
        else:
            raise ValueError(f"Worker with IP {worker.ip_address} is not busy.")

    def add_worker(self, worker: Worker):
        if worker.ip_address not in self.dict_free_workers and worker.ip_address not in self.dict_busy_workers:
            self.dict_free_workers[worker.ip_address] = worker
        else:
            raise ValueError(f"Worker with IP {worker.ip_address} already exists.")

    def remove_worker(self, worker: Worker):
        if worker.ip_address in self.dict_free_workers:
            del self.dict_free_workers[worker.ip_address]
        elif worker.ip_address in self.dict_busy_workers:
            del self.dict_busy_workers[worker.ip_address]
        else:
            raise ValueError(f"Worker with IP {worker.ip_address} does not exist.")


orchestrator = WorkerOrchestrator()


def get_orchestrator():
    """
    Returns the global singleton instance of the Orchestrator.
    """
    return orchestrator
