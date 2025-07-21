import os

os.environ["DJANGO_SETTINGS_MODULE"] = "embark.settings.deploy"

import django
django.setup()

from django.core.handlers.wsgi import WSGIHandler

application = WSGIHandler()

from users.models import User
from django import db

def check_password(environ, user, password):
    db.reset_queries()

    kwargs = {'username': user, 'is_active': True}

    try:
        try:
            user = User.objects.get(**kwargs)
        except User.DoesNotExist:
            return None

        if user.check_password(password):
            return True
        else:
            return False
    finally:
        db.connection.close()
