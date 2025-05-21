from typing import Optional
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