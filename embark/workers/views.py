import logging

from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import get_user
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from django.db.models import Count

from workers.forms import ConfigurationForm
from workers.orchestrator import get_orchestrator
from workers.models import DependencyState, Worker, Configuration, DependencyVersion, DependencyType, WorkerUpdate
from workers.update.update import queue_update
from workers.tasks import fetch_dependency_updates, worker_hard_reset_task, worker_soft_reset_task, undo_sudoers_file, config_worker_scan_task
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

        config_workers = Worker.objects.filter(configurations__id=config.id)
        for worker in config_workers:
            undo_sudoers_file.delay(worker.ip_address, config.ssh_user, config.ssh_password)

        workers = Worker.objects.annotate(config_count=Count('configurations')).filter(configurations__id=config_id, config_count=1)
        orchestrator = get_orchestrator()
        for worker in workers:
            orchestrator.remove_worker(worker, False)

            worker.dependency_version.delete()
            worker.delete()

        config.delete()
        messages.success(request, 'Configuration deleted successfully')
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

    new_config = config_form.save(commit=False)
    new_config.user = user
    new_config.save()

    messages.success(request, 'Configuration created successfully.')
    return safe_redirect(request, '/worker/')


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
    try:
        user = get_user(request)
        config = Configuration.objects.get(id=configuration_id)
        if not user_is_auth(user, config.user):
            messages.error(request, 'You are not allowed to access this configuration.')
            return safe_redirect(request, '/worker/')
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
    try:
        user = get_user(request)
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
    try:
        user = get_user(request)
        configuration = Configuration.objects.get(id=configuration_id)

        if not user_is_auth(user, configuration.user):
            messages.error(request, 'You are not allowed to access this configuration.')
            return safe_redirect(request, '/worker/')
    except Configuration.DoesNotExist:
        messages.error(request, 'Configuration not found.')
        return safe_redirect(request, '/worker/')

    workers = Worker.objects.filter(configurations__id=configuration_id)

    for worker in workers:
        worker_hard_reset(request, worker.id, configuration_id)

    messages.success(request, f'Successfully hard resetted configuration: {configuration_id} ({configuration.name})')
    return safe_redirect(request, '/worker/')


@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def worker_soft_reset(request, worker_id, configuration_id=None):
    """
    Soft reset the worker with the given worker ID.
    :params worker_id: The worker id
    :params configuration_id: The configuration id
    """
    try:
        if not worker_id:
            messages.error(request, 'No worker id given')
            return safe_redirect(request, '/worker/')

        user = get_user(request)
        worker = Worker.objects.get(id=worker_id)
        if not configuration_id:
            configuration = worker.configurations.filter(user=user).first()
        else:
            configuration = Configuration.objects.get(id=configuration_id)
        if not user_is_auth(user, configuration.user):
            messages.error(request, 'You are not allowed to access this worker.')
            return safe_redirect(request, '/worker/')

        try:
            worker_soft_reset_task.delay(worker.id)
            messages.success(request, f'Successfully soft resetted worker: ({worker.name})')
            return safe_redirect(request, '/worker/')
        except BaseException:
            messages.error(request, 'Soft Reset failed.')
            return safe_redirect(request, '/worker/')

    except (Worker.DoesNotExist, Configuration.DoesNotExist):
        messages.error(request, 'Worker or configuration not found.')
        return safe_redirect(request, '/worker/')


@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def worker_hard_reset(request, worker_id, configuration_id=None):
    """
    Hard reset the worker with the given worker ID.
    :params worker_id: The worker id
    :params configuration_id: The configuration id
    """
    try:
        if not worker_id:
            messages.error(request, 'No worker id given')
            return safe_redirect(request, '/worker/')
        if worker_id:
            user = get_user(request)
            worker = Worker.objects.get(id=worker_id)
            if not configuration_id:
                configuration = worker.configurations.filter(user=user).first()
            else:
                configuration = Configuration.objects.get(id=configuration_id)
            if not user_is_auth(user, configuration.user):
                messages.error(request, 'You are not allowed to access this worker.')
                return safe_redirect(request, '/worker/')

        try:
            worker_soft_reset_task.delay(worker.id)
            worker_hard_reset_task.delay(worker.id)
            messages.success(request, f'Successfully hard resetted worker: ({worker.name})')
            return safe_redirect(request, '/worker/')
        except BaseException:
            messages.error(request, 'Hard Reset failed.')
            return safe_redirect(request, '/worker/')

    except (Worker.DoesNotExist, Configuration.DoesNotExist):
        messages.error(request, 'Worker or configuration not found.')
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
    """
    # TODO: Create a template for this view instead of returning JSON
    update_queue = WorkerUpdate.objects.filter(worker__id=worker_id)
    update_queue = [{
        "dependency_type": update.get_type().label,
        "version": update.version
    } for update in update_queue]

    return JsonResponse({"update_queue": update_queue})


def dependency_state_reset(request):
    """
    Resets the used_by attribute of all dependency states.
    An incorrect shutdown of the embark application may leave this field
    populated with workers that no longer use the dependency.
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
