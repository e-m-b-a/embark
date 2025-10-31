__copyright__ = 'Copyright 2025 The AMOS Projects'
__author__ = 'ashiven, ClProsser, SirGankalot'
__license__ = 'MIT'

import logging
from io import StringIO
import os
from Crypto.PublicKey import RSA  # nosec

from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import get_user
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme

from workers.forms import ConfigurationForm
from workers.models import DependencyState, Worker, Configuration, DependencyVersion, DependencyType, WorkerUpdate
from workers.update.update import queue_update
from workers.tasks import fetch_dependency_updates, worker_hard_reset_task, worker_soft_reset_task, config_worker_scan_task, delete_config_task
from workers.orchestrator import get_orchestrator
from embark.helper import user_is_auth

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def worker_main(request):
    """
    Main view for the workers page.
    """
    user = get_user(request)
    configs = Configuration.objects.prefetch_related('workers').all()
    configs = configs.filter(user=user)
    configs = sorted(configs, key=lambda x: x.created_at, reverse=True)

    for config in configs:
        config.total_workers = config.workers.count()
        config.reachable_workers = config.workers.filter(reachable=True).count()
        config.scan_status = config.get_scan_status_display()

    reachable_workers = Worker.objects.filter(configurations__in=configs, reachable=True).distinct()
    unreachable_workers = Worker.objects.filter(configurations__in=configs, reachable=False).distinct()

    reachable_workers = sorted(reachable_workers, key=lambda x: x.ip_address)
    unreachable_workers = sorted(unreachable_workers, key=lambda x: x.ip_address)

    version = DependencyVersion.objects.first()
    if not version:
        version = DependencyVersion()

    workers = reachable_workers + unreachable_workers
    for worker in workers:
        worker.config_ids = ', '.join([str(config.id) for config in worker.configurations.filter(user=user)])
        worker.status = worker.get_status_display()

    update_pool = WorkerUpdate.objects.order_by('-created_at').filter(
        worker__configurations__user=user,
    ).select_related('worker')

    if update_pool:
        worker = update_pool[0].worker
        if worker.status == Worker.ConfigStatus.CONFIGURING:
            messages.info(request, f"Update for {worker.name} started: {update_pool[0].get_dependency_type_display()}")
        elif worker.status == Worker.ConfigStatus.CONFIGURED:
            messages.success(request, f"Update for {worker.name} finished: {update_pool[0].get_dependency_type_display()}")
        elif worker.status == Worker.ConfigStatus.ERROR:
            messages.error(request, f"Update for {worker.name} failed: {update_pool[0].get_dependency_type_display()}")

    return render(request, 'workers/index.html', {
        'user': user,
        'configs': configs,
        'workers': workers,
        'availableVersion': version
    })


@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def delete_config(request):
    """
    Delete a worker configuration and all workers associated with it. (If there are no other configs associated with the worker)
    """
    user = get_user(request)
    config_id = request.POST.get("configuration")
    if not config_id:
        messages.error(request, 'No configuration selected')
        return safe_redirect(request, '/worker/')

    try:
        config = Configuration.objects.get(id=config_id)
        if not user_is_auth(user, config.user):
            messages.error(request, 'You are not allowed to delete this configuration')
            return safe_redirect(request, '/worker/')

        delete_config_task.delay(config_id)
        messages.success(request, 'Configuration deletion queued')
    except Configuration.DoesNotExist:
        messages.error(request, 'Configuration not found')

    return safe_redirect(request, '/worker/')


@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def create_config(request):
    """
    Create a new configuration for workers.
    """
    user = get_user(request)

    config_form = ConfigurationForm(request.POST)
    if not config_form.is_valid():
        messages.error(request, 'Invalid configuration data.')
        return safe_redirect(request, '/worker/')

    new_config = config_form.save(commit=False)     # create new configuration
    new_config.user = user

    key = RSA.generate(settings.WORKER_SSH_KEY_SIZE)
    new_config.ssh_private_key = key.export_key(format="PEM", pkcs=8).decode("utf-8")
    new_config.ssh_public_key = key.publickey().export_key(format="OpenSSH").decode("utf-8")

    # Fix paramiko RSA peculiarity
    new_config.ssh_private_key = new_config.ssh_private_key.replace("PRIVATE KEY", "RSA PRIVATE KEY")

    new_config.save()

    messages.success(request, 'Configuration created successfully.')
    return safe_redirect(request, '/worker/')


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def download_ssh_private_key(request, configuration_id):
    """
    Download SSH private key
    :params configuration_id: The configuration id
    """
    try:
        user = get_user(request)
        config = Configuration.objects.get(id=configuration_id)
        if not user_is_auth(user, config.user):
            messages.error(request, 'You are not allowed to access this configuration.')
            return safe_redirect(request, '/worker/')
    except Configuration.DoesNotExist:
        messages.error(request, 'Configuration not found.')
        return safe_redirect(request, '/worker/')

    file = StringIO(config.ssh_private_key)
    response = HttpResponse(file, content_type="text/plain")
    response["Content-Disposition"] = "attachment; filename=private.key"
    return response


@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def configure_worker(request, configuration_id):
    """
    Configure all workers that are in the given configuration and have not been configured yet.
    :params configuration_id: The configuration id
    """
    workers = Worker.objects.filter(configurations__id=configuration_id, status__in=[Worker.ConfigStatus.UNCONFIGURED, Worker.ConfigStatus.ERROR])

    for worker in workers:
        queue_update(worker, DependencyType.DEPS)
        queue_update(worker, DependencyType.REPO)
        queue_update(worker, DependencyType.EXTERNAL)
        queue_update(worker, DependencyType.DOCKERIMAGE)

    return safe_redirect(request, '/worker/')


def _trigger_worker_update(worker, dependency: str):
    """
    Parses dependency and starts update thread
    :params worker: the worker to update
    :params dependency: the dependency as string
    :returns: true on success
    """
    parsed_dependency = None
    match dependency:
        case "emba":
            repo_res = _trigger_worker_update(worker, "repo")
            docker_res = _trigger_worker_update(worker, "docker")
            return repo_res and docker_res
        case "repo":
            parsed_dependency = DependencyType.REPO
        case "docker":
            parsed_dependency = DependencyType.DOCKERIMAGE
        case "external":
            parsed_dependency = DependencyType.EXTERNAL
        case "deps":
            parsed_dependency = DependencyType.DEPS
        case _:
            raise ValueError("Invalid dependency: Dependency could not be parsed.")

    queue_update(worker, parsed_dependency)

    return True


@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def update_worker_dependency(request, worker_id):
    """
    Update specific worker dependency
    :params worker_id: The worker id
    """
    dependency = request.POST.get("update")
    try:
        worker = Worker.objects.get(id=worker_id)

        _trigger_worker_update(worker, dependency)
    except Worker.DoesNotExist:
        messages.error(request, 'Worker does not exist')
        return safe_redirect(request, '/worker/')
    except ValueError as exception:
        messages.error(request, str(exception))
        return safe_redirect(request, '/worker/')

    messages.success(request, 'Update queued')
    messages.info(request, 'Please make sure to refresh the website to show status updates')
    return safe_redirect(request, '/worker/')


@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def update_configuration_dependency(request, configuration_id):
    """
    Update specific configuration dependency
    :params configuration_id: The configuration id
    """
    dependency = request.POST.get("update")
    workers = Worker.objects.filter(configurations__id=configuration_id, status__in=[Worker.ConfigStatus.CONFIGURED, Worker.ConfigStatus.CONFIGURING, Worker.ConfigStatus.ERROR])

    try:
        for worker in workers:
            _trigger_worker_update(worker, dependency)
    except ValueError as exception:
        messages.error(request, str(exception))
        return safe_redirect(request, '/worker/')

    messages.success(request, 'Update queued')
    messages.info(request, 'Please make sure to refresh the website to show status updates')
    return safe_redirect(request, '/worker/')


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def config_worker_scan(request, configuration_id):
    """
    For a given configuration scan its IP range and register all workers found in the range.
    For this, we create a worker object for each detected worker and
    assign each worker a name, its IP, and the given configuration.

    If a worker registration has already been processed for the configuration,
    gives information about the number of reachable workers out of the registered ones.
    :params configuration_id: The configuration id
    """
    user = get_user(request)
    if not user_is_auth(user, config.user):
        messages.error(request, 'You are not allowed to access this configuration.')
        return safe_redirect(request, '/worker/')
    try:
        config = Configuration.objects.get(id=configuration_id)
    except Configuration.DoesNotExist:
        messages.error(request, 'Configuration not found.')
        return safe_redirect(request, '/worker/')

    config_worker_scan_task.delay(config.id)
    messages.success(request, f'Scan for configuration: {config.name} has been queued.')
    return safe_redirect(request, '/worker/')


@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def configuration_soft_reset(request, configuration_id):
    """
    Soft resets all workers in a given configuration
    :params configuration_id: The configuration id
    """
    user = get_user(request)
    try:
        configuration = Configuration.objects.get(id=configuration_id)

        if not user_is_auth(user, configuration.user):
            messages.error(request, 'You are not allowed to access this configuration.')
            return safe_redirect(request, '/worker/')
    except Configuration.DoesNotExist:
        messages.error(request, 'Configuration not found.')
        return safe_redirect(request, '/worker/')

    workers = Worker.objects.filter(configurations__id=configuration_id)

    for worker in workers:
        worker_soft_reset(request, worker.id)

    messages.success(request, f'Successfully soft resetted configuration: {configuration_id} ({configuration.name})')
    return safe_redirect(request, '/worker/')


@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def configuration_hard_reset(request, configuration_id):
    """
    Hard resets all workers in a given configuration
    :params configuration_id: The configuration id
    """
    user = get_user(request)
    try:
        configuration = Configuration.objects.get(id=configuration_id)

        if not user_is_auth(user, configuration.user):
            messages.error(request, 'You are not allowed to access this configuration.')
            return safe_redirect(request, '/worker/')
    except Configuration.DoesNotExist:
        messages.error(request, 'Configuration not found.')
        return safe_redirect(request, '/worker/')

    workers = Worker.objects.filter(configurations__id=configuration_id)

    for worker in workers:
        worker_hard_reset(request, worker.id)

    messages.success(request, f'Successfully hard resetted configuration: {configuration_id} ({configuration.name})')
    return safe_redirect(request, '/worker/')


@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def worker_soft_reset(request, worker_id):
    """
    Soft reset the worker with the given worker ID.
    :params worker_id: The worker id
    """
    user = get_user(request)
    try:
        worker = Worker.objects.get(id=worker_id)
        configuration = worker.configurations.filter(user=user).first()

        if not user_is_auth(user, configuration.user):
            messages.error(request, 'You are not allowed to access this worker.')
            return safe_redirect(request, '/worker/')

        worker_soft_reset_task.delay(worker.id)
        messages.success(request, f'Worker soft reset queued: {worker.name}')
    except Worker.DoesNotExist:
        messages.error(request, 'Worker or configuration not found.')
    except Configuration.DoesNotExist:
        messages.error(request, 'You are not allowed to access this worker.')

    return safe_redirect(request, '/worker/')


@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def worker_hard_reset(request, worker_id):
    """
    Hard reset the worker with the given worker ID.
    :params worker_id: The worker id
    """
    user = get_user(request)
    try:
        worker = Worker.objects.get(id=worker_id)
        configuration = worker.configurations.filter(user=user).first()

        if not user_is_auth(user, configuration.user):
            messages.error(request, 'You are not allowed to access this worker.')
            return safe_redirect(request, '/worker/')

        worker_hard_reset_task.delay(worker.id)
        messages.success(request, f'Worker {worker.name} hard reset queued')
    except Worker.DoesNotExist:
        messages.error(request, 'Worker or configuration not found.')
    except Configuration.DoesNotExist:
        messages.error(request, 'You are not allowed to access this worker.')

    return safe_redirect(request, '/worker/')


@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def check_updates(request):
    """
    Checks if new updates are available
    """
    fetch_dependency_updates.delay()

    messages.success(request, 'Update check queued!')
    return safe_redirect(request, '/worker/')


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def orchestrator_reset(request):
    """
    Resets the orchestrator, clearing all tasks, soft resetting all workers, and marking
    them as free.
    """
    orchestrator = get_orchestrator()
    orchestrator.reset()

    messages.success(request, 'Orchestrator reset successfully. Please wait a minute for worker soft resets to complete.')
    return safe_redirect(request, '/worker/')


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def orchestrator_state(request):
    """
    Shows orchestrator information, including free and busy workers and current tasks.
    """
    # TODO: Create a template for this view instead of returning JSON
    orchestrator = get_orchestrator()

    return JsonResponse({"orchestrator_state": orchestrator.get_current_state()})


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def update_queue_reset(request, worker_id):
    """
    Clears the update queue for a worker.
    :param worker_id: The worker for which to delete updates
    """
    WorkerUpdate.objects.filter(worker__id=worker_id).delete()

    messages.success(request, 'Update queue reset successfully.')
    return safe_redirect(request, '/worker/')


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def update_queue_state(request, worker_id):
    """
    Shows the current update queue for a worker.
    :param worker_id: The worker for which to list updates
    """
    # TODO: Create a template for this view instead of returning JSON
    update_queue = WorkerUpdate.objects.filter(worker__id=worker_id)
    update_queue = [{
        "dependency_type": update.get_type().label,
        "version": update.version
    } for update in update_queue]

    return JsonResponse({"update_queue": update_queue})


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def dependency_state_reset(request):
    """
    Reset the 'used_by' field for all DependencyState instances.
    An unexpected shutdown may leave this field populated with workers
    that no longer use the dependency.
    """
    states = DependencyState.objects.all()
    for state in states:
        state.used_by.clear()
        state.save()

    messages.success(request, 'Dependency states reset successfully.')
    return safe_redirect(request, '/worker/')


def dependency_state(request):
    """
    Shows the current state of all dependencies.
    """
    # TODO: Create a template for this view instead of returning JSON
    states = DependencyState.objects.all()
    states = [{
        "dependency_type": state.dependency_type,
        "used_by": [worker.name for worker in state.used_by.all()],
        "availability": state.availability
    } for state in states]

    return JsonResponse({"states": states})


def safe_redirect(request, default):
    referer = request.META.get('HTTP_REFERER', default)
    if not url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}):
        referer = default
    return HttpResponseRedirect(referer)


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def show_worker_log(request, worker_id):
    """
    Show the logs of a specific worker.
    :params worker_id: The worker id
    """
    user = get_user(request)

    if not user_is_auth(user, configuration.user):
        messages.error(request, 'You are not allowed to access this worker.')
        return safe_redirect(request, '/worker/')

    try:
        worker = Worker.objects.get(id=worker_id)
        configuration = worker.configurations.filter(user=user).first()

        log_file = worker.log_location
        if not log_file or not os.path.isfile(log_file.path):
            messages.error(request, 'Log file not found for this worker.')
            return safe_redirect(request, '/worker/')
        with open(log_file.path, 'r') as file:
            log_content = file.read()

        return render(request, 'workers/worker_log.html', {
            'worker': worker,
            'log_content': log_content
        })
    except Worker.DoesNotExist:
        messages.error(request, 'Worker or configuration not found.')
    except Configuration.DoesNotExist:
        messages.error(request, 'You are not allowed to access this worker.')

    return safe_redirect(request, '/worker/')
