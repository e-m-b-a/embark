__copyright__ = 'Copyright 2022-2025 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

from random import randrange
import os
from pathlib import Path

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


def count_emba_modules(emba_dir_path):
    s_module_cnt, p_module_cnt, q_module_cnt, l_module_cnt, f_module_cnt, d_module_cnt = 0, 0, 0, 0, 0, 0
    for mod_file_ in os.listdir(f"{emba_dir_path}/modules"):
        if mod_file_.startswith('S'):
            s_module_cnt += 1
        elif mod_file_.startswith('P'):
            p_module_cnt += 1
        elif mod_file_.startswith('F'):
            f_module_cnt += 1
        elif mod_file_.startswith('L'):
            l_module_cnt += 1
        elif mod_file_.startswith('Q'):
            q_module_cnt += 1
        elif mod_file_.startswith('D'):
            d_module_cnt += 1
    return s_module_cnt, p_module_cnt, q_module_cnt, l_module_cnt, f_module_cnt, d_module_cnt


def get_version_strings():
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

    if Path(f"{settings.BASE_DIR}/VERSION.txt").exists():
        with open(Path(f"{settings.BASE_DIR}/VERSION.txt"), 'r', encoding='UTF-8') as embark_version_file:
            embark_version = embark_version_file.read().splitlines()[0]
    elif Path(f"{settings.BASE_DIR.parent}/VERSION.txt").exists():
        with open(Path(f"{settings.BASE_DIR.parent}/VERSION.txt"), 'r', encoding='UTF-8') as embark_version_file:
            embark_version = embark_version_file.read().splitlines()[0]
    else:
        embark_version = ""

    return embark_version, emba_version, stable_emba_version, container_version, nvd_version, github_emba_version


def user_is_staff(user):
    return user.is_staff


if __name__ == '__main__':
    TEST_STRING = 'Linux / v2.6.33.2'
    print(cleanup_charfield(TEST_STRING))

    print(count_emba_modules(emba_dir_path="/home/cylox/embark/emba"))
