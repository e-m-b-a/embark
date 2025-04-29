__copyright__ = 'Copyright 2025 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

from django.conf import settings


def embark_version(request):
    return {'EMBARK_VERSION': settings.VERSION}
