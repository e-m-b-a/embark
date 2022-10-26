import logging
import csv
import json
import os

from pathlib import Path
import re
from textwrap import indent

from django.conf import settings

from dashboard.models import Result
from uploader.archiver import Archiver
from uploader.models import FirmwareAnalysis

logger = logging.getLogger(__name__)


def import_log_dir(log_path, analysis_id):
    """
    1. copy into settings.EMBA_LOG_ROOT with id
    2. read csv into result result_model
    Args:
        current location
        object with needed pk
    return: 0/1
    """
    logger.info("Importing log for %s", analysis_id)
    if Archiver.unpack(file_location=log_path, extract_dir=Path(f"{settings.EMBA_LOG_ROOT}/{analysis_id}/emba_logs/")):
        return True
    logger.error("Error in import function, could not copy directory: %s", log_path)
    return False


def result_read_in(analysis_id):
    """
    calls read for all files inside csv_logs and stores its contents into the Result model

    :return: success->result_obj fail->None 
    """
    dir = f"{settings.EMBA_LOG_ROOT}/{analysis_id}/emba_logs/csv_logs/"
    csv_list = [os.path.join(dir, _file) for _file in os.listdir(dir)]
    for _file in csv_list:
        if _file.isfile():      # TODO change check. > if valid EMBA csv file
            logger.debug("File %s found and attempting to read", _file)
            res_dict = read_csv(path=_file)

            res_dict.pop('FW_path', None)
            entropy_value = res_dict.get("entropy_value", 0)
            # if type(entropy_value) is str:
            if isinstance(entropy_value, str):
                # entropy_value = re.findall(r'(\d+\.?\d*)', ' 7.55 bits per byte.')[0]
                entropy_value = re.findall(r'(\d+\.?\d*)', entropy_value)[0]
                entropy_value = entropy_value.strip('.')

            res = Result.objects.update_or_create(
                firmware_analysis=FirmwareAnalysis.objects.get(id=analysis_id),
                emba_command=res_dict.get("emba_command", ''),
                architecture_verified=res_dict.get("architecture_verified", ''),
                # os_unverified=res_dict.get("os_unverified", ''),
                os_verified=res_dict.get("os_verified", ''),
                files=int(res_dict.get("files", 0)),
                directories=int(res_dict.get("directories", 0)),
                entropy_value=float(entropy_value),
                shell_scripts=int(res_dict.get("shell_scripts", 0)),
                shell_script_vulns=int(res_dict.get("shell_script_vulns", 0)),
                kernel_modules=int(res_dict.get("kernel_modules", 0)),
                kernel_modules_lic=int(res_dict.get("kernel_modules_lic", 0)),
                interesting_files=int(res_dict.get("interesting_files", 0)),
                post_files=int(res_dict.get("post_files", 0)),
                canary=int(res_dict.get("canary", 0)),
                canary_per=int(res_dict.get("canary_per", 0)),
                relro=int(res_dict.get("relro", 0)),
                relro_per=int(res_dict.get("relro_per", 0)),
                no_exec=int(res_dict.get("no_exec", 0)),
                no_exec_per=int(res_dict.get("no_exec_per", 0)),
                pie=int(res_dict.get("pie", 0)),
                pie_per=int(res_dict.get("pie_per", 0)),
                stripped=int(res_dict.get("stripped", 0)),
                stripped_per=int(res_dict.get("stripped_per", 0)),
                bins_checked=int(res_dict.get("bins_checked", 0)),
                strcpy=int(res_dict.get("strcpy", 0)),
                strcpy_bin=json.dumps(res_dict.get("strcpy_bin", {})),
                versions_identified=int(res_dict.get("versions_identified", 0)),
                cve_high=int(res_dict.get("cve_high", 0)),
                cve_medium=int(res_dict.get("cve_medium", 0)),
                cve_low=int(res_dict.get("cve_low", 0)),
                exploits=int(res_dict.get("exploits", 0)),
                metasploit_modules=int(res_dict.get("metasploit_modules", 0)),
                certificates=int(res_dict.get("certificates", 0)),
                certificates_outdated=int(res_dict.get("certificates_outdated", 0)),
            )
            logger.debug("Result for %s created or updated", analysis_id)
        logger.error("Cant find file for %s", analysis_id)
        res = None    
    return res


def read_csv(path):
    """
    This job reads the csv file 

    :return: result_dict
    """
    res_dict = {}
    with open(path, newline='\n', encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=';')
        csv_list = []
        for row in csv_reader:
            # remove NAs from csv
            if row[-1] == "NA":
                row.pop(-1)
            csv_list.append(row)
            for ele in csv_list:
                if len(ele) == 2:
                    res_dict[ele[0]] = ele[1]
                elif len(ele) == 3:
                    if not ele[0] in res_dict.keys():
                        res_dict[ele[0]] = {}
                    res_dict[ele[0]][ele[1]] = ele[2]
                else:
                    pass

    logger.info("result dict: %s", res_dict)
    return res_dict


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    TEST_DIR = os.path.join(BASE_DIR, 'test/porter')

    # test print f50
    with open(os.path.join(TEST_DIR, 'test.json'), 'w', encoding='utf-8') as json_file:
        json_file.write(json.dumps(read_csv(os.path.join(TEST_DIR, 'test.csv')), indent=4))