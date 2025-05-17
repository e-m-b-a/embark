from django.http import JsonResponse

from workers.models import Worker
from users.models import Configuration

# TODO: add dependencies to SBOM and elsewhere
import paramiko
import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor


def config_worker_scan_and_registration(request, configuration_id):
    """
    For a given configuration scan its IP range and register all workers found in the range.
    For this, we create a worker object for each detected worker and
    assign each worker a name, its IP, and the given configuration.
    """
    configuration = Configuration.objects.get(id=configuration_id)
    ip_range = configuration.ip_range
    ip_network = ipaddress.ip_network(ip_range, strict=False)

    def connect_ssh(ip, port=22, timeout=1):
        try:
            with socket.create_connection((str(ip), port), timeout):
                new_worker = Worker(
                    configuration=configuration,
                    name=f"worker-{str(ip)}",
                    ip_address=str(ip),
                    system_info={}
                )
                new_worker.save()
                return str(ip)
        except:
            return None

    with ThreadPoolExecutor(max_workers=50) as executor:
        reachable_hosts = list(filter(None, executor.map(connect_ssh, list(ip_network.hosts()))))

    return JsonResponse({'status': 'scan_complete', 'reachable_hosts': reachable_hosts})


def registered_workers(request, configuration_id):
    """
    Get all registered workers for a given configuration.
    """
    configuration = Configuration.objects.get(id=configuration_id)
    workers = Worker.objects.filter(configuration=configuration)
    worker_list = [{'id': worker.id, 'name': worker.name, 'ip_address': worker.ip_address, 'system_info': worker.system_info} for worker in workers]
    return JsonResponse({'status': 'success', 'configuration': configuration.name, 'workers': worker_list})


def connect_worker(request, worker_id):
    """
    Connect to the worker with the given ID and gather system information.
    This information is comprised of OS type and version, CPU count, RAM size, Disk size,
    """
    worker = Worker.objects.get(id=worker_id)
    worker_name = worker.name
    worker_ip = worker.ip_address
    configuration = worker.configuration
    ssh_user = configuration.ssh_user
    ssh_password = configuration.ssh_password

    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(worker_ip, username=ssh_user, password=ssh_password)

    _stdin, stdout, _stderr = ssh_client.exec_command("grep PRETTY_NAME /etc/os-release")
    os_info = stdout.read().decode().strip()[len('PRETTY_NAME='):-1].strip('"')

    _stdin, stdout, _stderr = ssh_client.exec_command("nproc")
    cpu_info = stdout.read().decode().strip() + " cores"

    _stdin, stdout, _stderr = ssh_client.exec_command("free -h | grep Mem")
    ram_info = stdout.read().decode().strip().split()[1]
    ram_info = ram_info.replace('Gi', 'GB').replace('Mi', 'MB')

    _stdin, stdout, _stderr = ssh_client.exec_command("df -h | grep '^/'")
    disk_str = stdout.read().decode().strip().split('\n')[0].split()
    disk_total = disk_str[1].replace('G', 'GB').replace('M', 'MB')
    disk_free = disk_str[3].replace('G', 'GB').replace('M', 'MB')
    disk_info = f"Total: {disk_total}, Free: {disk_free}"

    ssh_client.close()

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
