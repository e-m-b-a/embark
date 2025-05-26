from typing import Dict
from workers.models import Worker
from users.models import Configuration

    
class WorkerOrchestrator:
    def __init__(self):
        self.workers: Dict[str, Worker] = {}
        self.dict_free_workers: Dict[str, Worker] = {}
        self.dict_busy_workers: Dict[str, Worker] = {}
        
    def list_workers(self) -> Dict[str, Dict]:
        return {ip: worker.to_dict() for ip, worker in self.workers.items()}
    
    def get_busy_workers(self) -> Dict[str, Worker]:
        return self.dict_busy_workers
    
    def get_free_workers(self) -> Dict[str, Worker]:
        return self.dict_free_workers

    def get_worker(self, ip_address: str, configuration: Configuration):
        try:
            existing_worker = Worker.objects.get(ip_address=str(ip_address))
            if configuration not in existing_worker.configurations.all():
                existing_worker.configurations.add(configuration)
                existing_worker.save()
            self.workers[ip_address] = existing_worker
            self.dict_free_workers[ip_address] = existing_worker
            return existing_worker
                
        except Worker.DoesNotExist:
            new_worker = Worker(
                configurations=[configuration],
                name=f"worker-{str(ip_address)}",
                ip_address=str(ip_address),
                system_info={}
            )
            new_worker.save()
            self.workers[ip_address] = new_worker
            self.dict_free_workers[ip_address] = new_worker
            return new_worker

        
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

    # def get_worker_info(self, ip_address: str) -> Optional[Dict]:
    #     worker = self.workers.get(ip_address)
    #     if worker:
    #         return worker.to_dict()
    #     else:
    #         raise ValueError(f"No worker found with IP {ip_address}")

    # def list_workers(self) -> Dict[str, Dict]:
    #     return {ip: worker.to_dict() for ip, worker in self.workers.items()}

    # def set_worker_status(self, ip_address: str, status: WorkerStatus, job_id: Optional[str] = None):
    #     if ip_address not in self.workers:
    #         raise ValueError(f"No worker found with IP {ip_address}")
    #     worker = self.workers[ip_address]
    #     if status == WorkerStatus.BUSY and job_id:
    #         worker.assign_job(job_id)
    #     elif status == WorkerStatus.FREE:
    #         worker.release()
    #     else:
    #         raise ValueError("Invalid status or missing job ID for BUSY status")