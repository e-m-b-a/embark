__copyright__ = 'Copyright 2022-2025 Siemens Energy AG, Copyright 2025 The AMOS Projects'
__author__ = 'Benedikt Kuehne, ashiven'
__license__ = 'MIT'

import socket
from random import randrange
import os
from pathlib import Path
import subprocess

from django.conf import settings


def rnd_rgb_color():
    """
    Used for html colors ONLY
    """
    result = "rgb("
    for _value in range(2):                         # nosec
        result += str(randrange(255)) + ", "    # nosec
    return result + str(randrange(255)) + ")"   # nosec


def rnd_rgb_full():
    """
    Used for html colors ONLY
    """
    return "rgb(" + str(randrange(255)) + ", " + str(randrange(255)) + ", " + str(randrange(255)) + ", " + "0.2)"   # nosec


def get_size(start_path='.'):
    """
    returns directory size in bytes
    https://stackoverflow.com/questions/1392413/calculating-a-directorys-size-using-python
    """
    total_size = 0
    for dirpath, _dirnames, filenames in os.walk(start_path):
        for file in filenames:
            file_path = os.path.join(dirpath, file)
            # skip if it is symbolic link
            if not os.path.islink(file_path):
                total_size += os.path.getsize(file_path)

    return total_size


def zip_check(content_list):
    """
    checks the contents against a pre defined list to ensure validity
    """
    check_list = [
        "emba_logs/html-report/emba.html",
        "emba_logs/html-report/index.html",
        "emba_logs/emba.log",
        "emba_logs/csv_logs/f50_base_aggregator.csv"]
    return all(value_ in content_list for value_ in check_list)


def cleanup_charfield(charfield) -> str:
    # clean-up for linux extensive os-descriptions
    if charfield.startswith("Linux"):
        charfield = charfield.split("/", 2)[:2]
        charfield = f"{charfield[0]}{charfield[1]}"
        charfield = (charfield[:16] + '..') if len(charfield) > 18 else charfield
    return charfield


def get_emba_modules(emba_dir_path) -> dict:
    """
    {
        S_Modules: [
            ('s02', 'S02_UEFI_FwHunt'),
            ...
        ],
        P_modules : [...]
    }
    """
    module_dict = {
        "S_Modules": [],
        "P_Modules": [],
        "Q_Modules": [],
        "L_Modules": [],
        "F_Modules": [],
        "D_Modules": [],
    }
    for mod_file_ in os.listdir(f"{emba_dir_path}/modules"):
        if os.path.isfile(os.path.join(f"{emba_dir_path}/modules", mod_file_)):
            if mod_file_.startswith('S'):
                module_dict["S_Modules"].append((str(mod_file_.split("_", 1)[0]).lower(), str(mod_file_)[:-3]))
            elif mod_file_.startswith('P'):
                module_dict["P_Modules"].append((str(mod_file_.split("_", 1)[0]).lower(), str(mod_file_)[:-3]))
            elif mod_file_.startswith('F'):
                module_dict["F_Modules"].append((str(mod_file_.split("_", 1)[0]).lower(), str(mod_file_)[:-3]))
            elif mod_file_.startswith('L'):
                module_dict["L_Modules"].append((str(mod_file_.split("_", 1)[0]).lower(), str(mod_file_)[:-3]))
            elif mod_file_.startswith('Q'):
                module_dict["Q_Modules"].append((str(mod_file_.split("_", 1)[0]).lower(), str(mod_file_)[:-3]))
            elif mod_file_.startswith('D'):
                module_dict["D_Modules"].append((str(mod_file_.split("_", 1)[0]).lower(), str(mod_file_)[:-3]))
    return module_dict


def count_emba_modules(module_dict):
    s_module_cnt = len(module_dict["S_Modules"])
    p_module_cnt = len(module_dict["P_Modules"])
    q_module_cnt = len(module_dict["Q_Modules"])
    l_module_cnt = len(module_dict["L_Modules"])
    f_module_cnt = len(module_dict["F_Modules"])
    d_module_cnt = len(module_dict["D_Modules"])
    return s_module_cnt, p_module_cnt, q_module_cnt, l_module_cnt, f_module_cnt, d_module_cnt


def get_version_strings():
    if Path(f"{settings.BASE_DIR}/VERSION.txt").exists():
        with open(Path(f"{settings.BASE_DIR}/VERSION.txt"), 'r', encoding='UTF-8') as embark_version_file:
            embark_version = embark_version_file.read().splitlines()[0]
    elif Path(f"{settings.BASE_DIR.parent}/VERSION.txt").exists():
        with open(Path(f"{settings.BASE_DIR.parent}/VERSION.txt"), 'r', encoding='UTF-8') as embark_version_file:
            embark_version = embark_version_file.read().splitlines()[0]
    else:
        embark_version = ""

    return embark_version


def get_emba_version():
    # gets us the currently installed version
    if Path(settings.EMBA_ROOT + "/external/onlinechecker").exists():
        # get the latest version nnumbers
        with open(Path(settings.EMBA_ROOT + "/external/onlinechecker/EMBA_VERSION.txt"), 'r', encoding='UTF-8') as emba_version_file:
            stable_emba_version = emba_version_file.read().splitlines()[0]
        with open(Path(settings.EMBA_ROOT + "/external/onlinechecker/EMBA_CONTAINER_HASH.txt"), 'r', encoding='UTF-8') as container_version_file:
            container_version = container_version_file.read().splitlines()[0]
        with open(Path(settings.EMBA_ROOT + "/external/onlinechecker/NVD_HASH.txt"), 'r', encoding='UTF-8') as nvd_version_file:
            nvd_version = nvd_version_file.read().splitlines()[0]
        with open(Path(settings.EMBA_ROOT + "/external/onlinechecker/EMBA_GITHUB_HASH.txt"), 'r', encoding='UTF-8') as emba_github_version_file:
            github_emba_version = emba_github_version_file.read().splitlines()[0]
    else:
        stable_emba_version = ""
        container_version = ""
        nvd_version = ""
        github_emba_version = ""

    if Path(settings.EMBA_ROOT + "/config/VERSION.txt").exists():
        with open(Path(settings.EMBA_ROOT + "/config/VERSION.txt"), 'r', encoding='UTF-8') as emba_version_file:
            emba_version = emba_version_file.read().splitlines()[0]
    else:
        emba_version = ""

    return emba_version, stable_emba_version, container_version, nvd_version, github_emba_version


def user_is_auth(req_user, own_user):
    """
    Checks if the request user is allowed to access a resource owned by another user.
    Returns True if the user is authorized, otherwise False.
    :param req_user: The user who is requesting access to the logs.
    :param own_user: The user whose logs are being requested.
    :return: True if authorized, False otherwise.
    """
    if req_user.is_superuser:
        return True
    elif req_user.is_staff:
        return True
    elif req_user == own_user:
        return True
    elif req_user.team == own_user.team:
        return True
    elif req_user.groups.filter(name='Administration_Group').exists() and own_user.team is None:
        return True
    return False


def disk_space_check(directory: str = "/var/www/embark/", size: int = 4000000) -> bool:
    """
    Checks if the disk space is sufficient for the application.
    Returns True if sufficient, False otherwise.

    DO NOT USE WITH USER_INPUT!!!

    DEFAULT = 4GB in KB
    """
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist.")
        return False
    try:
        output = subprocess.check_output(['df', '-l', directory]).decode('utf-8')  # nosec
        available_space = int(output.splitlines()[1].split()[3])  # Get the available space in KB
        # print(f"Available disk space: {available_space} KB")
        if available_space < size:
            return False
    except Exception as exception:
        print(f"Error checking disk space: {exception}")
        return False
    return True


def is_ip_local_host(ip_address: str) -> bool:
    """
    Checks if the given IP address is a local host address.
    Returns True if it is a local host address, otherwise False.
    inspired by https://gist.github.com/bennr01/7043a460155e8e763b3a9061c95faaa0
    """
    try:
        hostname = socket.getfqdn(ip_address)
        if hostname in ("localhost", "0.0.0.0"):
            return True
        localhost = socket.gethostname()
        localaddrs = socket.getaddrinfo(localhost, 22)  # port 22 is arbitrary here
        targetaddrs = socket.getaddrinfo(hostname, 22)
        for (family, socktype, proto, canonname, sockaddr) in localaddrs:
            for (rfamily, rsocktype, rproto, rcanonname, rsockaddr) in targetaddrs:
                if rsockaddr[0] == sockaddr[0]:
                    return True
        return False
    except socket.error:
        return False


if __name__ == '__main__':
    # import pprint
    # TEST_STRING = 'Linux / v2.6.33.2'
    # print(cleanup_charfield(TEST_STRING))
    # emba_modle_list = get_emba_modules(emba_dir_path="/home/cylox/embark/emba")
    # print(pprint.pformat(emba_modle_list, indent=1))
    # print(count_emba_modules(emba_modle_list))
    if disk_space_check('./'):
        print("Disk space is sufficient.")
    print(is_ip_local_host("127.0.0.1"))
    print(is_ip_local_host("172.22.0.1"))
