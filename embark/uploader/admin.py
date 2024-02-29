__copyright__ = 'Copyright 2021-2024 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'Benedikt Kuehne, m-1-k-3, diegiesskanne'
__license__ = 'MIT'

from django.contrib import admin

from uploader.models import FirmwareAnalysis

admin.site.register(FirmwareAnalysis)
