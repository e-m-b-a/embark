from subprocess import Popen, PIPE
import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def check_tz() -> bool:
    cmd = f"date +%Z"
    process = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    system_tz, _error = process.communicate()
    ret_code = process.returncode
    if ret_code != 0 :
        logger.error("check_tz.error: %s", _error)
        return False
    system_tz = system_tz.decode("utf-8").rstrip()
    if system_tz != timezone.get_current_timezone_name(): 
        logger.error("SystemTZ=%s and EMBArkTZ=%s are not the same!", system_tz, timezone.get_current_timezone_name())
        return False
    logger.debug("SystemTZ=%s and EMBArkTZ=%s are the same!", system_tz, timezone.get_current_timezone_name())
    return True


check_tz()
