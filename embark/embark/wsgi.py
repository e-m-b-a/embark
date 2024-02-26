"""
WSGI config for djangoProject project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""
__copyright__ = 'Copyright 2021-2024 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'Benedikt Kuehne, diegiesskanne'

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'embark.settings.dev')

application = get_wsgi_application()
