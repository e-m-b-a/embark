import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def get_emba_root():
    """
    Gets EMBA root considering if workers are enabled
    :returns: path to emba folder
    """
    # TODO: Add Worker check
    # pylint: disable=W0125
    return settings.EMBA_ROOT if False else settings.WORKER_EMBA_ROOT


def get_emba_base_cmd():
    """
    Constructs EMBA base command
    :returns: EMBA base command
    """
    return f"sudo DISABLE_STATUS_BAR=1 DISABLE_NOTIFICATIONS=1 HTML=1 FORMAT_LOG=1 {get_emba_root()}/emba"
