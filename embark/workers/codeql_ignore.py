__copyright__ = 'Copyright 2025 The AMOS Projects'
__author__ = 'ashiven'
__license__ = 'MIT'

import paramiko


def new_autoadd_client():
    """
    Create a new Paramiko SSH client with the AutoAddPolicy set for missing host keys.
    """
    ssh_client = paramiko.SSHClient()
    ssh_client.load_system_host_keys()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    return ssh_client
