from typing import Dict, Optional
from enum import Enum


class WorkerStatus(Enum):
    FREE = "free"
    BUSY = "busy" 

class Worker:
    def __init__(self, ip_address: str):
        self.ip_address = ip_address
        self.status = WorkerStatus.FREE
        self.job_id: Optional[str] = None

    def assign_job(self, job_id: str):
        self.status = WorkerStatus.BUSY
        self.job_id = job_id

    def release(self):
        self.status = WorkerStatus.FREE
        self.job_id = None

    def to_dict(self):
        return {
            "ip_address": self.ip_address,
            "status": self.status,
            "job_id": self.job_id
        }
        
    def is_free(self):
        return self.status == WorkerStatus.FREE
    
class WorkerOrchestrator:
    def __init__(self):
        self.workers: Dict[str, Worker] = {}

    def register_worker(self, ip_address: str):
        if ip_address not in self.workers:
            self.workers[ip_address] = Worker(ip_address)
        else:
            raise ValueError(f"Worker with IP {ip_address} already registered.")

    def get_worker_info(self, ip_address: str) -> Optional[Dict]:
        worker = self.workers.get(ip_address)
        if worker:
            return worker.to_dict()
        else:
            raise ValueError(f"No worker found with IP {ip_address}")

    def list_workers(self) -> Dict[str, Dict]:
        return {ip: worker.to_dict() for ip, worker in self.workers.items()}

    def set_worker_status(self, ip_address: str, status: WorkerStatus, job_id: Optional[str] = None):
        if ip_address not in self.workers:
            raise ValueError(f"No worker found with IP {ip_address}")
        worker = self.workers[ip_address]
        if status == WorkerStatus.BUSY and job_id:
            worker.assign_job(job_id)
        elif status == WorkerStatus.FREE:
            worker.release()
        else:
            raise ValueError("Invalid status or missing job ID for BUSY status")