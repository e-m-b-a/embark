__copyright__ = 'Copyright 2025 The AMOS Projects'
__author__ = 'ClProsser'
__license__ = 'MIT'

from django.conf import settings
from settings.helper import workers_enabled


def get_emba_root():
    """
    Gets EMBA root considering if workers are enabled
    :returns: path to emba folder
    """
    return settings.WORKER_EMBA_ROOT if workers_enabled() else settings.EMBA_ROOT


def get_emba_base_cmd():
    """
    Constructs EMBA base command
    :returns: EMBA base command
    """
    return f"sudo DISABLE_STATUS_BAR=1 DISABLE_NOTIFICATIONS=1 HTML=1 FORMAT_LOG=1 {get_emba_root()}/emba"
