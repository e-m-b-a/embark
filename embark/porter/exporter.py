__copyright__ = 'Copyright 2022-2025 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

import logging
# from django.conf import settings

logger = logging.getLogger(__name__)


def result_json(analysis_id):
    """
    returns json of result as Posix Path
    """
    _ = analysis_id  # TODO
    return {'test': "testexport"}
