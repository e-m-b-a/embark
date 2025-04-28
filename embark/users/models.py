__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'Garima Chauhan, m-1-k-3, Benedikt Kuehne'
__license__ = 'MIT'

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class Team(models.Model):
    name = models.CharField(primary_key=True, verbose_name="name", max_length=150, unique=True)
    is_active = models.BooleanField(default=True, help_text='Whether this Team is active or not')
    created = models.DateTimeField(auto_now_add=True, help_text='Date time when this entry was created')
    modified = models.DateTimeField(auto_now=True, help_text='Date time when this entry was modified')


class User(AbstractUser):
    timezone = models.CharField(max_length=32, choices=settings.TIMEZONES, default='UTC')
    email = models.EmailField(verbose_name="email address", blank=True, unique=True)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, editable=True, related_name='member_of_team')
    is_active_member = models.BooleanField(default=True, help_text='Whether this team member is active or not')
    api_key = models.CharField(max_length=64, blank=True, null=True, help_text="API key of the user")

    class Meta:
        default_permissions = ()    # disable "add", "change", "delete" and "view" default permissions
        permissions = (
            ("user_permission", "Can access user menues of embark"),
            ("tracker_permission", "Can access tracker functionalities of embark"),
            ("updater_permission", "Can access updater functionalities of embark"),
            ("uploader_permission_minimal", "Can access uploader functionalities of embark"),
            ("uploader_permission_advanced", "Can access all uploader functionalities of embark"),
            ("porter_permission", "Can access porter functionalities of embark"),
            ("reporter_permission", "Can access reporter functionalities of embark"),
            ("dashboard_permission_minimal", "Can access dashboard functionalities of embark"),
            ("dashboard_permission_advanced", "Can access all dashboard functionalities of embark"),
        )