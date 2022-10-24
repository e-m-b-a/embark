import logging
import os
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


def result_json(analysis_id):
    """
    returns file_name as str
    """
    if os.path.isdir(f"{settings.EMBA_LOG_ROOT}/{analysis_id}/"):
        try:
            with open(f"{settings.EMBA_LOG_ROOT}/{analysis_id}/export.json", 'w', encoding='utf-8'):
                # data = serializers.serialize("json", Result.objects.filter(firmware_analysis=analysis_id))
                # json write TODO
                pass
        except FileExistsError:
            logger.error("File exists")
    return Path(f"{analysis_id}/export.json")
