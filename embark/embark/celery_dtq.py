__copyright__ = 'Copyright 2025 The AMOS Projects'
__author__ = 'ClProsser'
__license__ = 'MIT'


import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'embark.settings.deploy')

app = Celery('embark')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
