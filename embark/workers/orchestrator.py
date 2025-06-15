from typing import Dict
from collections import deque
from workers.models import Worker
from workers.tasks import start_analysis


class OrchestratorTask:
    def __init__(self, firmware_analysis_id: str, emba_cmd: str, src_path: str, target_path: str):
        self.firmware_analysis_id = firmware_analysis_id
        self.emba_cmd = emba_cmd
        self.src_path = src_path
        self.target_path = target_path


class WorkerOrchestrator:
    def __init__(self):
        self.dict_free_workers: Dict[str, Worker] = {}
        self.dict_busy_workers: Dict[str, Worker] = {}
        self.task_queue = deque()

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
                map_worker_array[worker_ip] = f"analysis: {worker.analysis_id}"
            else:
                raise ValueError(f"Worker with IP {worker_ip} does not exist.")
        return map_worker_array

    def assign_task(self, task: OrchestratorTask):
        if not self.dict_free_workers:
            self.task_queue.append(task)
        else:
            free_worker = next(iter(self.dict_free_workers.values()))
            if not self.task_queue:
                self.assign_worker(free_worker, task)
            else:
                queued_task = self.task_queue.popleft()
                self.assign_worker(free_worker, queued_task)
                self.assign_task(task)

    def assign_worker(self, worker: Worker, task: OrchestratorTask):
        if worker.ip_address not in self.dict_free_workers:
            raise ValueError(f"Worker with IP {worker.ip_address} is already busy.")

        worker.analysis_id = task.firmware_analysis_id
        worker.save()
        start_analysis.delay(worker.id, task.emba_cmd, task.src_path, task.target_path)

        self.dict_busy_workers[worker.ip_address] = worker
        del self.dict_free_workers[worker.ip_address]

    def release_worker(self, worker: Worker):
        if worker.ip_address not in self.dict_busy_workers:
            raise ValueError(f"Worker with IP {worker.ip_address} is not busy.")

        if self.task_queue:
            next_task = self.task_queue.popleft()
            self.dict_free_workers[worker.ip_address] = worker
            del self.dict_busy_workers[worker.ip_address]
            self.assign_worker(worker, next_task)
        else:
            self.dict_free_workers[worker.ip_address] = worker
            del self.dict_busy_workers[worker.ip_address]
            worker.analysis_id = None
            worker.save()

    def add_worker(self, worker: Worker):
        if worker.ip_address in self.dict_free_workers or worker.ip_address in self.dict_busy_workers:
            raise ValueError(f"Worker with IP {worker.ip_address} already exists.")

        self.dict_free_workers[worker.ip_address] = worker

    def remove_worker(self, worker: Worker):
        if worker.ip_address in self.dict_free_workers:
            del self.dict_free_workers[worker.ip_address]
        elif worker.ip_address in self.dict_busy_workers:
            del self.dict_busy_workers[worker.ip_address]
        else:
            raise ValueError(f"Worker with IP {worker.ip_address} does not exist.")
