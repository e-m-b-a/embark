__copyright__ = 'Copyright 2021-2024 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'm-1-k-3, Maximilian Wagner, Benedikt Kuehne'
__license__ = 'MIT'

import logging
import psutil

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django_apscheduler import util

from uploader.models import ResourceTimestamp

logger = logging.getLogger("web")

CPU_UPPER_BOUND = 90
MEMORY_UPPER_BOUND = 80


def resource_tracker():
    """
    This job tracks the current cpu and memory usage and stores Timestamp objects
    in the db for further usage.

    """
    cpu_percentage = psutil.cpu_percent()
    memory_percentage = psutil.virtual_memory().percent

    # inform user about high load
    # if cpu_percentage > CPU_UPPER_BOUND:
    #    logger.warning(f"High CPU usage: {cpu_percentage}%")
    # if memory_percentage > MEMORY_UPPER_BOUND:
    #    logger.warning(f"High Memory usage: {memory_percentage}%")

    # save timestamps in db
    res_timestamp = ResourceTimestamp(cpu_percentage=cpu_percentage, memory_percentage=memory_percentage)
    res_timestamp.save()


@util.close_old_connections
def delete_old_job_executions(max_age=1_209_600):
    """
    This job deletes APScheduler job execution entries older than `max_age` from the database,
    as well as deleting all timestamps older than 'max_age'
    It helps to prevent the database from filling up with old historical records that are no
    longer useful.

    :param max_age: The maximum length of time to retain historical job execution records.
                    Defaults to 14 days.
    """
    # delete job execution entries
    DjangoJobExecution.objects.delete_old_job_executions(max_age)

    # delete entries in db older than 2 weeks
    time_delta = timezone.now() - timezone.timedelta(seconds=max_age)
    ResourceTimestamp.objects.all().filter(timestamp__lt=time_delta).delete()


class Command(BaseCommand):     # FIXME change cycle times
    """
    Extends Base command to feature another command called runapscheduler by the manage.py script
    like this "python3 manage.py runapscheduler"
    """

    help = "Runs resource tracker as well as cleanup process."

    def add_arguments(self, parser):
        # Named optional argument
        parser.add_argument(
            '--test',
            action='store_true',
            help='sample every minute for testing purpose',
        )

    def handle(self, *args, **options):
        """
        handler for runapscheduler command
        """
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # configure CronTrigger
        if options['test']:
            # Every hour -> changed to 5 seconds
            resource_tracker_trigger = CronTrigger(second="*/5")
            # every 30 minutes
            delete_old_job_executions_tigger = CronTrigger(minute="*/30")
            delete_old_than = 900
        else:
            # Every hour
            resource_tracker_trigger = CronTrigger(minute="00")
            # everyday at midnight
            delete_old_job_executions_tigger = CronTrigger(hour="00", minute="00")
            delete_old_than = 1_209_600

        # start resource_tracker
        scheduler.add_job(
            resource_tracker,
            trigger=resource_tracker_trigger,
            id="resource_tracker",
            max_instances=1,
            replace_existing=True,
        )
        logger.info("Added CronTrigger job %s.", resource_tracker.__name__)
        logger.info("Added CronTrigger resource_tracker_trigger: %s.", resource_tracker_trigger)
        logger.info("Added CronTrigger delete_old_job_executions_trigger: %s.", delete_old_job_executions_tigger)

        # start cleanup jobresource_tracker
        scheduler.add_job(
            delete_old_job_executions,
            trigger=delete_old_job_executions_tigger,
            id="delete_old_job_executions",
            max_instances=1,
            replace_existing=True,
            args=(delete_old_than,)
        )
        logger.info("Added weekly job: 'delete_old_job_executions'.")

        try:
            logger.info("Starting scheduler for tracking...")
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("Stopping scheduler for tracking...")
            scheduler.shutdown()
            logger.info("Scheduler for tracking shut down successfully!")
