__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'Benedikt Kuehne, m-1-k-3, diegiesskanne'
__license__ = 'MIT'

from django.contrib import admin

from uploader.models import FirmwareAnalysis, FirmwareFile, Device, Label, Vendor

admin.site.register(FirmwareAnalysis)
admin.site.register(Device)
admin.site.register(FirmwareFile)
admin.site.register(Label)
admin.site.register(Vendor)
