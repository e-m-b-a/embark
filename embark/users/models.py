__copyright__ = 'Copyright 2021-2024 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'Garima Chauhan, m-1-k-3, Benedikt Kuehne'
__license__ = 'MIT'

import enum

from django.db import models
from django.contrib.auth.models import AbstractUser, Group
from django.conf import settings

from lib.choice_enum import ChoiceIntEnum


@enum.unique
class Role(ChoiceIntEnum):
    VIEWER = 0
    EDITOR = 1
    OWNER = 2
    MANAGER = 3


class Team(Group):
    is_active = models.BooleanField(default=True, help_text='Whether this Team is active or not')
    created = models.DateTimeField(auto_now_add=True, help_text='Date time when this entry was created')
    modified = models.DateTimeField(auto_now=True, help_text='Date time when this entry was modified')


class User(AbstractUser):
    timezone = models.CharField(max_length=32, choices=settings.TIMEZONES, default='UTC')
    email = models.EmailField(verbose_name="email address", blank=True, unique=True)
    team = models.ManyToManyField(Team, blank=True, related_name='member_of_team')
    team_role = models.IntegerField(choices=Role.choices(), default=Role.VIEWER)
    is_active_member = models.BooleanField(default=True, help_text='Whether this team member is active or not')
