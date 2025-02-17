__copyright__ = 'Copyright 2022-2025 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

from django.contrib import admin
from porter.models import LogZipFile

admin.site.register(LogZipFile)
