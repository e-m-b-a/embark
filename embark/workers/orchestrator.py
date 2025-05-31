from typing import Dict, Tuple
from workers.models import Worker
from collections import deque


class WorkerOrchestrator:
    def __init__(self):
        self.dict_free_workers: Dict[str, Worker] = {}
        self.dict_busy_workers: Dict[str, Tuple[str, Worker]]
        self.next_task = deque()

    def get_busy_workers(self) -> Dict[str, Tuple[str, Worker]]:
        return self.dict_busy_workers

    def get_free_workers(self) -> Dict[str, Worker]:
        return self.dict_free_workers
    
    def assign_task(self, task: str):
        if not self.dict_free_workers:
            if self.next_task:
                self.next_task.append(task)
                return ValueError("No free workers available, task added to the queue.")
        
        worker_ip, worker = next(iter(self.dict_free_workers.items()))
        self.assign_worker(worker, task)
        return worker_ip

    def assign_worker(self, worker: Worker, task: str):
        if worker.ip_address not in self.dict_free_workers:
            self.next_task.append(task)
        if worker.ip_address in self.dict_free_workers:
            self.dict_busy_workers[worker.ip_address] = (task, worker)
            del self.dict_free_workers[worker.ip_address]
        else:
            raise ValueError(f"Worker with IP {worker.ip_address} is already busy.")

    def release_worker(self, worker: Worker):
        if worker.ip_address in self.dict_busy_workers:
            self.dict_free_workers[worker.ip_address] = worker
            del self.dict_busy_workers[worker.ip_address]
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
