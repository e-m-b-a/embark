import paramiko
from celery import shared_task
from celery.utils.log import get_task_logger
from scp import SCPClient
from django.utils.timezone import now, timedelta
from django.conf import settings
import os

from workers.views import update_system_info
from workers.models import Worker
from workers.orchestrator import WorkerOrchestrator
from uploader.models import FirmwareAnalysis

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
            print(f"[Worker {worker.id}] Sync is disabled. Not rescheduling.")
            return

        print(f"[Worker {worker.id}] Sync running...")
        fetch_analysis_logs(worker.id, worker.job_id)

        # Reschedule task
        sync_worker_analysis.apply_async((worker.id,), eta=now() + timedelta(minutes=schedule_minutes))
        print(f"[Worker {worker.id}] Rescheduled sync in {str(schedule_minutes)} minutes.")

    except Exception as ex:
        print(f"[Worker {worker.id}] Unexpected exception: {ex}")
        return

def fetch_analysis_logs(worker_id, analysis_id):
    try:
        worker = Worker.objects.get(id=worker_id)

        # FIXME: This assumes the same emba directory for the worker as the orchestrator
        remote_path = f"{settings.EMBA_LOG_ROOT}/{worker.job_id}/emba_logs/"
        local_path = f"{settings.EMBA_LOG_ROOT}/{worker.job_id}/emba_logs/"

        # Create local dir
        os.makedirs(local_path, exist_ok=True)

        ssh_client = worker.ssh_connect()
        with SCPClient(ssh_client.get_transport()) as scp:
            scp.get(remote_path, local_path, recursive=True)
        print(f"[Worker {worker.id}] FirmwareAnalysis {analysis_id} successfully saved to {path}.")

    except FirmwareAnalysis.DoesNotExist as ex:
        print(f"[Worker {worker.id}] FirmwareAnalysis {analysis_id} does not exist: {ex}")
        return
    except Worker.DoesNotExist as ex:
        print(f"[Worker {worker.id}] Worker does not exist: {ex}")
        return
    except Exception as ex:
        print(f"[Worker {worker.id}] Unexpected exception: {ex}")
        return

# @shared_task
def update_orchestrator_status():
    orchestrator = WorkerOrchestrator()
    busy_workers = orchestrator.get_busy_workers()

    for id, worker in busy_workers.items():

        # TODO: add the next line after the status is properly implemented
            # worker.status == Worker.ConfigStatus.CONFIGURING or \
        if not worker.reachable or \
            worker.status == Worker.ConfigStatus.UNCONFIGURED or \
            worker.status == Worker.ConfigStatus.ERROR:
            print(f"[Worker {worker.id}] Skipping unavailable worker...")
            continue

        # Updates the status
        worker.status = get_worker_status(worker)

        if worker.status == Worker.ConfigStatus.RUNNING:
            # Check if analysis is actually running
            # Check if Docker container is still running
            # Set "Running" in GUI
            print(f"[Worker {worker.id}] Analysis {worker.job_id} is running.")
            continue
        if worker.status == Worker.ConfigStatus.FINISHED:
            # worker.job_id = null
            # Set to free in orchestrator and save
            # Set "Finished" in GUI
            print(f"[Worker {worker.id}] Analysis {worker.job_id} finished.")
            continue
        if worker.status == Worker.ConfigStatus.FAILED:
            # worker.job_id = null
            # Set to free in orchestrator and save
            # Set "Failed" in GUI
            print(f"[Worker {worker.id}] Analysis {worker.job_id} failed.")
            continue

def get_worker_status(worker) -> Worker.ConfigStatus:
    """
    Checks and returns the status of the worker's availability.
    """
    try:
        if not worker.job_id:
            raise RuntimeError(f"[Worker {worker.id}] Error: job_id is unassigned")

        analysis = FirmwareAnalysis.objects.get(id=worker.job_id)

        # TODO: Think about if this makes sense. These fields SHOULD always be set correctly.
        # Is there a need at all to check emba.log???
        if analysis.finished:
            return Worker.ConfigStatus.FINISHED
        if analysis.failed:
            return Worker.ConfigStatus.FAILED

        # Otherwise infer the status from emba.log
        return check_emba_log_status(analysis)

    except Exception as ex:
        print(f"[Worker {worker.id}] Unexpected exception: {ex}")
        return

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
            return Worker.ConfigStatus.FINISHED
        else:
            print(f"[Worker {worker.id}] Analysis is still running: {output}")
            return Worker.ConfigStatus.RUNNING

    except Exception as ex:
        print(f"[Worker {worker.id}] Unexpected exception: {ex}")
        return

