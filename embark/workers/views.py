from django.http import JsonResponse

from workers.models import Worker

# TODO: add dependency to SBOM and elsewhere
import paramiko


def register_new_worker(request):
    """
    Register a new worker. The configurations of the user are fetched and the 
    worker automatically gets assigned the configuration whose IP range matches its
    IP address. The worker is then added to the database and we return the ID assigned to the worker.
    """
    # TODO: implement
    # we may alternatively implement it so that there is a worker scan for each
    # configuration of the user and all detected workers are registered using 
    # something like this endpoint


def connect_worker(request, worker_id):
    """
    Connect to the worker with the given ID and gather system information.
    This information is comprised of OS type and version, CPU count, RAM size, Disk size,
    """
    worker = Worker.objects.get(worker_id=worker_id)
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
    ram_info = stdout.read().decode().strip()[len('Mem:'):].strip().split()[1]
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

    return JsonResponse({'worker_id': worker_id, 'worker_name': worker_name, 'system_info': worker.system_info})
