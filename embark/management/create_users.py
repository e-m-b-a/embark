__copyright__ = 'Copyright 2025 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

from django.core.management import BaseCommand
from django.contrib.auth.models import User
import logging


USERS = {
    "dummy" : ["New_User","member@domain.cu","1234*"],
}

class Command(BaseCommand):

    help = "Creates default permission groups for users"

    def handle(self, *args, **options):

        for user_name in USERS:

            new_user = None
            if user_name == "Admin":
                new_user, created = User.objects.get_or_create(username=user_name,is_staff = True,is_superuser = True, email = USERS[user_name][1])
            else:
                new_user, created = User.objects.get_or_create(username=user_name,is_staff = True, email = USERS[user_name][1])

            new_user.set_password(USERS[user_name][2])
            new_user.save()
