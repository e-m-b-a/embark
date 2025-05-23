import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor

from django.shortcuts import render
import paramiko

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import get_user
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.http import JsonResponse

from workers.models import Worker
from users.models import Configuration


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def workers_main(request):
    """
    Main view for the workers page.
    """
    user = get_user(request)
    return render(request, 'workers/index.html', {
        'user': user
    })


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
    """
    try:
        user = get_user(request)
        configuration = Configuration.objects.get(id=configuration_id)
        if user != configuration.user:
            return JsonResponse({'status': 'error', 'message': 'You are not allowed to access this configuration.'})
    except Configuration.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Configuration not found.'})

    ip_range = configuration.ip_range
    ip_network = ipaddress.ip_network(ip_range, strict=False)

    def connect_ssh(ip_address, port=22, timeout=1):
        try:
            with socket.create_connection((str(ip_address), port), timeout):
                try:
                    existing_worker = Worker.objects.get(ip_address=str(ip_address))
                    if configuration not in existing_worker.configurations.all():
                        existing_worker.configurations.add(configuration)
                        existing_worker.save()
                except Worker.DoesNotExist:
                    new_worker = Worker(
                        configurations=[configuration],
                        name=f"worker-{str(ip_address)}",
                        ip_address=str(ip_address),
                        system_info={}
                    )
                    new_worker.save()
                return str(ip_address)
        except socket.timeout:
            return None

    with ThreadPoolExecutor(max_workers=50) as executor:
        reachable = list(filter(None, executor.map(connect_ssh, list(ip_network.hosts()))))

    registered = [worker.ip_address for worker in configuration.workers.all()]
    return JsonResponse({'status': 'scan_complete', 'configuration': configuration.name, 'registered_workers': registered, 'reachable_workers': reachable})


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.worker_permission", login_url='/')
def registered_workers(request, configuration_id):
    """
    Get detailed information about all registered workers for a given configuration.
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
    """
    try:
        user = get_user(request)
        worker = Worker.objects.get(id=worker_id)
        worker_name = worker.name
        worker_ip = worker.ip_address
        configuration = worker.configurations.get(id=configuration_id)
        if user != configuration.user:
            return JsonResponse({'status': 'error', 'message': 'You are not allowed to access this configuration.'})
        ssh_user = configuration.ssh_user
        ssh_password = configuration.ssh_password
    except (Worker.DoesNotExist, Configuration.DoesNotExist):
        return JsonResponse({'status': 'error', 'message': 'Worker or configuration not found.'})

    ssh_client = paramiko.SSHClient()
    # TODO: We may want to use paramiko.AutoAddPolicy() instead of paramiko.RejectPolicy()
    # to automatically add the host key to known hosts even though it is flagged as insecure by CodeQL.
    # With the RejectPolicy, we will not be able to connect to the worker if the host key is not already in known hosts
    ssh_client.load_system_host_keys()
    ssh_client.set_missing_host_key_policy(paramiko.RejectPolicy())

    try:
        ssh_client.connect(worker_ip, username=ssh_user, password=ssh_password)

        _stdin, stdout, _stderr = ssh_client.exec_command('grep PRETTY_NAME /etc/os-release')  # nosec B601: No user input
        os_info = stdout.read().decode().strip()[len('PRETTY_NAME='):-1].strip('"')

        _stdin, stdout, _stderr = ssh_client.exec_command('nproc')  # nosec B601: No user input
        cpu_info = stdout.read().decode().strip() + " cores"

        _stdin, stdout, _stderr = ssh_client.exec_command('free -h | grep Mem')  # nosec B601: No user input
        ram_info = stdout.read().decode().strip().split()[1]
        ram_info = ram_info.replace('Gi', 'GB').replace('Mi', 'MB')

        _stdin, stdout, _stderr = ssh_client.exec_command("df -h | grep '^/'")  # nosec B601: No user input
        disk_str = stdout.read().decode().strip().split('\n')[0].split()
        disk_total = disk_str[1].replace('G', 'GB').replace('M', 'MB')
        disk_free = disk_str[3].replace('G', 'GB').replace('M', 'MB')
        disk_info = f"Total: {disk_total}, Free: {disk_free}"

        ssh_client.close()
    except paramiko.SSHException as ssh_error:
        print(f"SSH connection failed: {ssh_error}")
        ssh_client.close()
        return JsonResponse({'status': 'error', 'message': 'SSH connection failed.'})

    system_info = {
        'os_info': os_info,
        'cpu_info': cpu_info,
        'ram_info': ram_info,
        'disk_info': disk_info
    }
    worker.system_info = system_info
    worker.save()

    return JsonResponse({
        'status': 'success',
        'worker_id': worker_id,
        'worker_name': worker_name,
        'worker_ip': worker_ip,
        'system_info': system_info
    })
