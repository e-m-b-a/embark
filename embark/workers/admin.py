__copyright__ = 'Copyright 2021-2025 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

from django.contrib import admin

from workers.models import Configuration, Worker

admin.site.register(Configuration)
admin.site.register(Worker)
