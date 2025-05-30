__copyright__ = 'Copyright 2022-2025 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

from django.contrib import admin

from dashboard.models import Result, Vulnerability, SoftwareInfo, SoftwareBillOfMaterial

admin.site.register(Result)
admin.site.register(Vulnerability)
admin.site.register(SoftwareInfo)
admin.site.register(SoftwareBillOfMaterial)
