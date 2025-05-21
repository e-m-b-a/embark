from orchestrator import Worker
    
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
    
if __name__ == "__main__":
    ip = "localhost"
    worker = Worker(ip)
    test_worker_is_free(worker)