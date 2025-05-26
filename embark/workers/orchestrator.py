from typing import Dict
from workers.models import Worker


class WorkerOrchestrator:
    def __init__(self):
        self.dict_free_workers: Dict[str, Worker] = {}
        self.dict_busy_workers: Dict[str, Worker] = {}

    def get_busy_workers(self) -> Dict[str, Worker]:
        return self.dict_busy_workers

    def get_free_workers(self) -> Dict[str, Worker]:
        return self.dict_free_workers

    def assign_worker(self, worker: Worker):
        if worker.ip_address in self.dict_free_workers:
            self.dict_busy_workers[worker.ip_address] = worker
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
