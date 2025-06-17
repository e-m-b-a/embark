import paramiko
import subprocess
import time
import requests
import os
import json
from celery import shared_task
from celery.utils.log import get_task_logger
from scp import SCPClient
from django.utils.timezone import now, timedelta
from django.conf import settings

from workers.views import update_system_info
from workers.models import Worker
from workers.orchestrator import WorkerOrchestrator
from uploader.models import FirmwareAnalysis
from uploader.boundedexecutor import BoundedExecutor


logger = get_task_logger(__name__)

def create_periodic_tasks(**kwargs):
    """
    Create periodic tasks with the start of the application. (called in ready() method of the app config)
    """
    from django_celery_beat.models import PeriodicTask, IntervalSchedule  # pylint: disable=import-outside-toplevel
    schedule, _created = IntervalSchedule.objects.get_or_create(
        every=2,
        period=IntervalSchedule.MINUTES
    )
    PeriodicTask.objects.get_or_create(
        interval=schedule,
        name='Update Worker Information',
        task='workers.tasks.update_worker_info',
    )


@shared_task
def update_worker_info():
    """
    Task to update system information for all workers.
    """
    workers = Worker.objects.all()
    for worker in workers:
        config = worker.configurations.first()
        try:
            logger.info("Updating worker %s", worker.name)
            update_system_info(config, worker)
            worker.reachable = True
        except paramiko.SSHException:
            logger.info("Worker %s is unreachable, setting status to offline.", worker.name)
            worker.reachable = False
        except BaseException as error:
            logger.info("An error occurred while updating worker %s: %s", worker.name, error)
            continue
        finally:
            worker.save()



@shared_task
def sync_worker_analysis(worker_id, schedule_minutes=5):
    try:
        worker = Worker.objects.get(id=worker_id)

        if not worker.sync_enabled:
            PeriodicTask.objects.filter(name=f"sync_worker_{worker.id}").delete()
            print(f"[Worker {worker.id}] Sync is disabled. Removed the scheduled task.")
            return

        print(f"[Worker {worker.id}] Sync running...")
        status = fetch_analysis_logs(worker.id, worker.job_id)

        if status == "finished":
            worker.sync_enabled = False
            worker.job_id = None
            worker.save()
            PeriodicTask.objects.filter(name=f"sync_worker_{worker.id}").delete()
            print(f"[Worker {worker.id}] Analysis finished. Turned off sync.")

    except Exception as ex:
        print(f"[Worker {worker.id}] Unexpected exception: {ex}")
        return

def fetch_analysis_logs(worker_id, analysis_id):
    """
    Queues zip creation on remote worker, fetches it, extracts it and updates the database.
    It is a blocking function.
    Returns "finished" if the analysis completed and the scheduled task can be deleted.
    """
    try:
        worker = Worker.objects.get(id=worker_id)

        # FIXME: This assumes the same emba directory for the worker as the orchestrator
        remote_path = f"{settings.MEDIA_ROOT}/log_zip/{worker.job_id}.zip"
        local_path =  f"{settings.MEDIA_ROOT}/log_zip/{worker.job_id}.zip"

        config = worker.configurations.first()

        # Queue zip generation
        url = f"http://{worker.ip_address}:8001/uploader/queue_zip/"
        payload = { "analysis_id": worker.job_id }
        response = requests.post(url, json=payload)
        json_format = json.loads(response.text)

        if json_format["status"] == "error":
            msg = json_format["message"]
            print(f"[Worker {worker.id}] Could not queue zip generation on remote machine: {msg}")

        # TODO: Make endpoint blocking (requires changes to BoundedExecutor)
        time.sleep(60)

        # Ensure log_zip/ exists
        os.makedirs(f"{settings.MEDIA_ROOT}/log_zip/", exist_ok=True)

        ssh_client = worker.ssh_connect()
        with SCPClient(ssh_client.get_transport()) as scp:
            scp.get(remote_path, local_path)

        BoundedExecutor.unzip_log(worker.job_id, local_path) # Blocking
        print(f"[Worker {worker.id}] Unzipped {local_path}.")

        if json_format["analysis_finished"]:
            return "finished"

    except Worker.DoesNotExist as ex:
        print(f"[Worker {worker.id}] Worker does not exist: {ex}")
    except Exception as ex:
        print(f"[Worker {worker.id}] Unexpected exception: {ex}")


def check_emba_log_status(analysis) -> Worker.ConfigStatus:
    """
    Checks emba.log and infers the status of the analysis.
    Returns Worker.ConfigStatus.FINISHED or
            Worker.ConfigStatus.RUNNING
    """
    try:
        path = f"{analysis.path_to_logs}/emba.log"
        n_lines = 10

        result = subprocess.run(['tail', '-n', "10", path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True)

        if result.stderr:
            raise RuntimeError(f"[Worker {worker.id}] Error calling '$ tail {path}': {result.stderr}")

        if "Test ended on" in result.stdout:
            print(f"[Worker {worker.id}] Analysis finished: {output}")
            return Worker.JobStatus.UNASIGNED
        else:
            print(f"[Worker {worker.id}] Analysis is still running: {output}")
            return Worker.JobStatus.RUNNING

    except Exception as ex:
        print(f"[Worker {worker.id}] Unexpected exception: {ex}")
        return

