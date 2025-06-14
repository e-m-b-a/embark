import paramiko
from celery import shared_task
from celery.utils.log import get_task_logger

from workers.views import update_system_info
from workers.models import Worker

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
