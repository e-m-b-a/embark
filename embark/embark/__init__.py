__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'Benedikt Kuehne, diegiesskanne'
__license__ = 'MIT'

from subprocess import Popen, PIPE
import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def check_tz() -> bool:
    cmd = "date +%Z"
    with Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE) as process:   # nosec
        system_tz, _error = process.communicate()
        ret_code = process.returncode
    if ret_code != 0:
        logger.error("check_tz.error: %s", _error)
        return False
    system_tz = system_tz.decode("utf-8").rstrip()
    if system_tz != timezone.get_current_timezone_name():
        logger.error("SystemTZ=%s and EMBArkTZ=%s are not the same!", system_tz, timezone.get_current_timezone_name())
        return False
    logger.debug("SystemTZ=%s and EMBArkTZ=%s are the same!", system_tz, timezone.get_current_timezone_name())
    return True


check_tz()
