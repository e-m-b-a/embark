import os

os.environ["DJANGO_SETTINGS_MODULE"] = "embark.settings.deploy"

import django
django.setup()

from django.core.handlers.wsgi import WSGIHandler
from django.contrib.auth.handlers.modwsgi import check_password  # pylint: disable=unused-import

application = WSGIHandler()
