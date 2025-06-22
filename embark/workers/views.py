import ipaddress
import socket
import re
from concurrent.futures import ThreadPoolExecutor

import paramiko

from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import get_user
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from django.db.models import Count

from workers.models import Worker, Configuration
from workers.update.dependencies import DependencyType, uses_dependency
from workers.tasks import update_worker, update_system_info, worker_hard_reset_task, worker_soft_reset_task


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

    reachable_workers = Worker.objects.filter(configurations__in=configs, reachable=True).distinct()
    unreachable_workers = Worker.objects.filter(configurations__in=configs, reachable=False).distinct()

    reachable_workers = sorted(reachable_workers, key=lambda x: x.ip_address)
    unreachable_workers = sorted(unreachable_workers, key=lambda x: x.ip_address)

    workers = reachable_workers + unreachable_workers
    for worker in workers:
        worker.config_ids = ', '.join([str(config.id) for config in worker.configurations.filter(user=user)])
        worker.status = worker.get_status_display()

    return render(request, 'workers/index.html', {
        'user': user,
        'configs': configs,
        'workers': workers,
    })


@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def delete_config(request):
    """
    Delete a worker configuration and all workers associated with it. (If there are no other configs associated with the worker)
    """
    user = get_user(request)
    selected_config_id = request.POST.get("configuration")
    if not selected_config_id:
        messages.error(request, 'No configuration selected')
        return safe_redirect(request, '/worker/')

    try:
        config = Configuration.objects.get(id=selected_config_id)
        if config.user != user:
            messages.error(request, 'You are not allowed to delete this configuration')
            return safe_redirect(request, '/worker/')

        workers = Worker.objects.annotate(config_count=Count('configurations')).filter(configurations__id=selected_config_id, config_count=1)
        workers.delete()

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
    name = request.POST.get("name")
    ssh_user = request.POST.get("ssh_user")
    ssh_password = request.POST.get("ssh_password")
    ip_range = request.POST.get("ip_range")

    if not ssh_user or not ssh_password or not ip_range or not name:
        messages.error(request, 'Name, SSH user, SSH password, and IP range are required.')
        return safe_redirect(request, '/worker/')

    ip_range_regex = r"^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$"
    if not re.match(ip_range_regex, ip_range):
        messages.error(request, 'Invalid IP range format. Use CIDR notation')
        return safe_redirect(request, '/worker/')

    Configuration.objects.create(
        name=name,
        user=user,
        ssh_user=ssh_user,
        ssh_password=ssh_password,
        ip_range=ip_range
    )
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
        update_worker.delay(worker.id, DependencyType.ALL.name)

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

    if uses_dependency(parsed_dependency, worker):
        return False

    update_worker.delay(worker.id, parsed_dependency.name)

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

        if not _trigger_worker_update(worker, dependency):
            messages.error(request, 'Worker update already queued')
            return safe_redirect(request, '/worker/')
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
    workers = Worker.objects.filter(configurations__id=configuration_id, status__in=[Worker.ConfigStatus.CONFIGURED])

    count = 0
    try:
        for worker in workers:
            if not _trigger_worker_update(worker, dependency):
                continue
            count = count + 1
    except ValueError as exception:
        messages.error(request, str(exception))
        return safe_redirect(request, '/worker/')

    if count > 0:
        messages.success(request, 'Update queued')
    else:
        messages.error(request, 'Configuration update already queued')
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
        configuration = Configuration.objects.get(id=configuration_id)
        if user != configuration.user:
            return JsonResponse({'status': 'error', 'message': 'You are not allowed to access this configuration.'})
    except Configuration.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Configuration not found.'})

    def update_or_create_worker(ip_address):
        try:
            existing_worker = Worker.objects.get(ip_address=str(ip_address))
            existing_worker.reachable = True
            existing_worker.save()
            if configuration not in existing_worker.configurations.all():
                existing_worker.configurations.add(configuration)
                existing_worker.save()
            try:
                update_system_info(configuration, existing_worker)
            except BaseException:
                pass
        except Worker.DoesNotExist:
            new_worker = Worker(
                name=f"worker-{str(ip_address)}",
                ip_address=str(ip_address),
                system_info={},
                reachable=True
            )
            new_worker.save()
            new_worker.configurations.set([configuration])
            try:
                update_system_info(configuration, new_worker)
            except BaseException:
                pass

    def connect_ssh(ip_address, port=22, timeout=1):
        try:
            with socket.create_connection((str(ip_address), port), timeout):
                update_or_create_worker(ip_address)
                return str(ip_address)
        except Exception:
            return None

    ip_range = configuration.ip_range
    ip_network = ipaddress.ip_network(ip_range, strict=False)
    with ThreadPoolExecutor(max_workers=50) as executor:
        reachable = list(filter(None, executor.map(connect_ssh, list(ip_network.hosts()))))

    registered = []
    for worker in configuration.workers.all():
        registered.append(worker.ip_address)
        if worker.ip_address not in reachable:
            worker.reachable = False
            worker.save()

    view_access = request.GET.get('view_access')
    if view_access == "True":
        messages.success(request, f"Scan complete. {len(reachable)} reachable workers out of {len(registered)} registered workers.")
        return safe_redirect(request, '/worker/')

    return JsonResponse({'status': 'scan_complete', 'configuration': configuration.name, 'registered_workers': registered, 'reachable_workers': reachable})


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

        if configuration.user != user:
            messages.error(request, 'You are not allowed to access this configuration.')
            return safe_redirect(request, '/worker/')
    except Configuration.DoesNotExist:
        messages.error(request, 'Configuration not found.')
        return safe_redirect(request, '/worker/')

    workers = Worker.objects.filter(configurations__id=configuration_id)

    for worker in workers:
        worker_soft_reset(request, worker.id, configuration_id)

    messages.success(request, f'Successfully soft reseted configuration: {configuration_id} ({configuration.name})')
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

        if configuration.user != user:
            messages.error(request, 'You are not allowed to access this configuration.')
            return safe_redirect(request, '/worker/')
    except Configuration.DoesNotExist:
        messages.error(request, 'Configuration not found.')
        return safe_redirect(request, '/worker/')

    workers = Worker.objects.filter(configurations__id=configuration_id)

    for worker in workers:
        worker_hard_reset(request, worker.id, configuration_id)

    messages.success(request, f'Successfully hard reseted configuration: {configuration_id} ({configuration.name})')
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
        if not configuration_id and not worker_id:
            messages.error(request, 'No worker id and no config id given')
            return safe_redirect(request, '/worker/')
        if worker_id:
            user = get_user(request)
            worker = Worker.objects.get(id=worker_id)
            if not configuration_id:
                configuration = worker.configurations.filter(user=user).first()
            else:
                configuration = Configuration.objects.get(id=configuration_id)
            if configuration.user != user:
                messages.error(request, 'You are not allowed to access this worker.')
                return safe_redirect(request, '/worker/')

        ssh_client = None
        try:
            worker_soft_reset_task.delay(worker=worker, configuration=configuration)
            messages.success(request, f'Successfully soft reseted worker: {worker.ip_address} ({worker.name})')
            return safe_redirect(request, '/worker/')

        except (paramiko.SSHException, socket.error):
            if ssh_client:
                ssh_client.close()
            messages.error(request, 'SSH connection failed or command execution failed.')
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
        if not configuration_id and not worker_id:
            messages.error(request, 'No worker id and no config id given')
            return safe_redirect(request, '/worker/')
        if worker_id:
            user = get_user(request)
            worker = Worker.objects.get(id=worker_id)
            if not configuration_id:
                configuration = worker.configurations.filter(user=user).first()
            else:
                configuration = Configuration.objects.get(id=configuration_id)
            if configuration.user != user:
                messages.error(request, 'You are not allowed to access this worker.')
                return safe_redirect(request, '/worker/')

        ssh_client = None
        try:
            worker_soft_reset(request, worker_id, configuration.id)
            worker_hard_reset_task.delay(worker=worker, configuration=configuration)
            messages.success(request, f'Successfully hard reseted worker: {worker.ip_address} ({worker.name})')
            return safe_redirect(request, '/worker/')

        except (paramiko.SSHException, socket.error):
            if ssh_client:
                ssh_client.close()
            messages.error(request, 'SSH connection failed or command execution failed.')
            return safe_redirect(request, '/worker/')

    except (Worker.DoesNotExist, Configuration.DoesNotExist):
        messages.error(request, 'Worker or configuration not found.')
        return safe_redirect(request, '/worker/')


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def registered_workers(request, configuration_id):
    """
    Get detailed information about all registered workers for a given configuration.
    :params configuration_id: The configuration id
    """
    try:
        user = get_user(request)
        configuration = Configuration.objects.get(id=configuration_id)
        if user != configuration.user:
            return JsonResponse({'status': 'error', 'message': 'You are not allowed to access this configuration.'})
    except Configuration.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Configuration not found.'})

    workers = configuration.workers.all()
    worker_list = [{'id': worker.id, 'name': worker.name, 'ip_address': worker.ip_address, 'system_info': worker.system_info} for worker in workers]
    return JsonResponse({'status': 'success', 'configuration': configuration.name, 'workers': worker_list})


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def connect_worker(request, configuration_id, worker_id):
    """
    Connect to the worker with the given worker ID using SSH credentials from the given config ID and gather system information.
    This information is comprised of OS type and version, CPU count, RAM size, and Disk size
    :params configuration_id: The configuration id
    :params worker_id: The worker id
    """
    try:
        user = get_user(request)
        worker = Worker.objects.get(id=worker_id)
        configuration = worker.configurations.get(id=configuration_id)
        if user != configuration.user:
            return JsonResponse({'status': 'error', 'message': 'You are not allowed to access this configuration.'})
    except (Worker.DoesNotExist, Configuration.DoesNotExist):
        return JsonResponse({'status': 'error', 'message': 'Worker or configuration not found.'})

    try:
        system_info = update_system_info(configuration, worker)
    except paramiko.SSHException:
        return JsonResponse({'status': 'error', 'message': 'Failed to retrieve system_info.'})

    return JsonResponse({
        'status': 'success',
        'worker_id': worker_id,
        'worker_name': worker.name,
        'worker_ip': worker.ip_address,
        'system_info': system_info
    })


def safe_redirect(request, default):
    referer = request.META.get('HTTP_REFERER', default)
    if not url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}):
        referer = default
    return HttpResponseRedirect(referer)
