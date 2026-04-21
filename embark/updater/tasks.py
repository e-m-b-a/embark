__copyright__ = 'Copyright 2026 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

from pyexpat.errors import messages
from subprocess import Popen, PIPE
from celery import shared_task
from django.conf import settings
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from celery.utils.log import get_task_logger

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import docker
import git
from requests import RequestException

from uploader.settings import get_emba_base_cmd

logger = get_task_logger(__name__)

def setup_periodic_tasks():
    """
    Setup periodic tasks for the updater
    """
    # Example: Setup a periodic task to check for updates every day
    schedule, created = IntervalSchedule.objects.get_or_create(
        every=1,
        period=IntervalSchedule.DAYS,
    )

    PeriodicTask.objects.get_or_create(
        interval=schedule,
        name='Check for EMBA updates',
        task='updater.tasks.check_for_updates',
    )

def check_for_updates(option):
    """
    Task to check for updates

    :param option: Check option 
    :return: None
    """
    logger.info("Checking for EMBA updates...")
    # Implement the logic to check for updates here
    # This could involve checking git repositories, Docker images, etc.
    logger.debug("Checking EMBA with: %s", option)
    try:
        cmd = f"cd {settings.EMBA_ROOT} && {get_emba_base_cmd(overwrite=True)} -d{option}"

        with open(f"{settings.EMBA_LOG_ROOT}/emba_update.log", "w+", encoding="utf-8") as file:
            proc = Popen(cmd, stdin=PIPE, stdout=file, stderr=file, shell=True)   # nosec
            # wait for completion
            proc.communicate()
            return_code = proc.wait()
        # success
        logger.info("Check Successful: %s", cmd)
        if return_code != 0:
            raise BaseException("EMBA has non zero exit-code")
    except BaseException as exce:
        logger.error("emba dep check error: %s", exce)

    room_group_name = "versions"
    channel_layer = get_channel_layer()
    # send ws message
    async_to_sync(channel_layer.group_send)(
        room_group_name, {
            "type": 'send.message',
            "message": {f"EMBA dep check {option}": return_code}
        }
    )

@shared_task
def emba_update(option):
    """
    Task to update EMBA components

    :param: option: Update option (NVD, DOCKER, PULL) as string
    :return: None
    """
    logger.info("Starting EMBA update...")
    # Implement the logic to update EMBA components here
    logger.debug("Updating EMBA with: %s", option)
    try:
        if option == 'NVD':
            logger.debug("NVD update selected, pulling latest changes from git")
            nvd_repo = git.Repo(settings.NVD_ROOT)
            output = nvd_repo.remotes.origin.pull('main')
            # Check if any new commits were fetched
            if not output:
                logger.info("NVD repository already up to date")
            else:
                logger.info(f"NVD repository updated: {output}")
            return_code = 0
        elif option == 'DOCKER':
            logger.debug("Docker update selected, pulling latest docker image")
            try:
                client = docker.from_env(timeout=5)
                # Old images are removed via a seperate task
                pulled_image = client.images.pull('embeddedanalyzer/emba:latest')
                logger.info(f"EMBA docker image repository pulled: {pulled_image.tags}")
                return_code = 0
            except docker.errors.APIError as docker_exce:
                logger.error("Docker API error during update: %s", docker_exce)
                return_code = 1
            except docker.errors.DockerException as docker_exce:
                logger.error("Docker connection error during update: %s", docker_exce)
                return_code = 1
        elif option == 'PULL':
            logger.debug("Git pull update selected, pulling latest changes from git")
            emba_repo = git.Repo(settings.EMBA_ROOT)
            output = emba_repo.remotes.origin.pull('master')
            # Check if any new commits were fetched
            if not output:
                logger.info("EMBA repository already up to date")
            else:
                logger.info(f"EMBA repository updated: {output}")
            # update external dir
            cmd = f"cd {settings.EMBA_ROOT} && {get_emba_base_cmd(overwrite=True)} -u{option}"
            logger.debug("Updating EMBA external data with: %s", cmd)
            with open(f"{settings.EMBA_LOG_ROOT}/emba_update.log", "w+", encoding="utf-8") as file:
                proc = Popen(cmd, stdin=PIPE, stdout=file, stderr=file, shell=True)   # nosec
                # wait for completion
                proc.communicate()
                return_code = proc.wait()
            # success
            logger.info("Update Successful: %s", cmd)
            if return_code != 0:
                raise BaseException("EMBA update has non zero exit-code")
        else:
            logger.error("Unknown update option selected: %s", option)
            raise Exception(f"Unknown update option selected: {option}")
    except (Exception, AssertionError, docker.errors.APIError) as exce:
        logger.error("emba update error: %s", exce)
        return_code = 1

    room_group_name = "versions"
    channel_layer = get_channel_layer()
    # send ws message
    async_to_sync(channel_layer.group_send)(
        room_group_name, {
            "type": 'send.message',
            "message": {f"EMBA update {option}": return_code}
        }
    )

    return return_code