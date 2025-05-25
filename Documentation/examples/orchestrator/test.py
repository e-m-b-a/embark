from orchestrator import Worker
from orchestrator import WorkerOrchestrator
from orchestrator import WorkerStatus
    
def test_worker_is_free(worker):
    print("Testing is_free method")
    # Check if worker is free
    print(worker.is_free())
    # Assign a job
    worker.assign_job("job_123")
    # Check if worker is free
    print(worker.is_free())
    # Release the job
    worker.release()
    # Check if worker is free
    print(worker.is_free())
    
def test_worker_orchestrator():
    print("Testing WorkerOrchestrator")
    orchestrator = WorkerOrchestrator()
    
    # register workers
    orchestrator.register_worker("localhost")
    orchestrator.register_worker("localhost2")
    orchestrator.register_worker("localhost3")
    # forcing an error by registering the same worker again
    try:
        orchestrator.register_worker("localhost")
    except ValueError as e:
        print(e)
    # force an error by trying to get info of a non-registered worker
    try:
        orchestrator.get_worker_info("non_existent_worker")
    except ValueError as e:
        print(e)
    
    # Get worker info
    worker_info = orchestrator.get_worker_info("localhost")
    print(worker_info)
    # List all workers
    all_workers = orchestrator.list_workers()
    print(all_workers)
    # set worker status to busy
    orchestrator.set_worker_status("localhost", WorkerStatus.BUSY, "job_456")
    # Get updated worker info
    updated_worker_info = orchestrator.get_worker_info("localhost")
    print(updated_worker_info)
    # Set worker status to free
    orchestrator.set_worker_status("localhost", WorkerStatus.FREE)
    # get final worker info
    final_worker_info = orchestrator.get_worker_info("localhost")
    print(final_worker_info)
    
    
if __name__ == "__main__":
    ip = "localhost"
    worker = Worker(ip)
    test_worker_is_free(worker)
    test_worker_orchestrator()