__copyright__ = 'Copyright 2021-2024 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'Garima Chauhan, m-1-k-3, Benedikt Kuehne'

import enum

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

from lib.choice_enum import ChoiceIntEnum


@enum.unique
class Role(ChoiceIntEnum):
    VIEWER = 0
    EDITOR = 1
    OWNER = 2
    MANAGER = 3


class Team(models.Model):
    name = models.CharField(max_length=150, unique=True, help_text='Name of the team')
    is_active = models.BooleanField(default=True, help_text='Whether this Team is active or not')
    created = models.DateTimeField(auto_now_add=True, help_text='Date time when this entry was created')
    modified = models.DateTimeField(auto_now=True, help_text='Date time when this entry was modified')


class User(AbstractUser):
    is_active = models.BooleanField(default=True, help_text='User active or not')
    created = models.DateTimeField(auto_now_add=True, help_text='Date time when this entry was created')
    modified = models.DateTimeField(auto_now=True, help_text='Date time when this entry was modified')
    timezone = models.CharField(max_length=32, choices=settings.TIMEZONES, default='UTC')


class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='team_member')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_team_member')
    role = models.IntegerField(choices=Role.choices(), default=Role.VIEWER)
    is_active = models.BooleanField(default=True, help_text='Whether this team member is active or not')
    created = models.DateTimeField(auto_now_add=True, help_text='Date time when this entry was created')
    modified = models.DateTimeField(auto_now=True, help_text='Date time when this entry was modified')
