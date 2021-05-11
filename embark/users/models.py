from django.db import models
from django.contrib.auth.models import AbstractUser

from embark.lib.choice_enum import ChoiceIntEnum
import enum


@enum.unique
class Role(ChoiceIntEnum):
    viewer = 0
    editor = 1
    owner = 2
    manager = 3


class Team(models.Model):
    name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this Team is active or not'
        ,
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)


class User(AbstractUser):
    is_active = models.BooleanField(
        default=True,
        help_text='Designates whether this user should be treated as active. '
                  'Unselect this instead of deleting accounts.'
        ,
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)


class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='team_member')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_team_member')
    role = models.IntegerField(choices=Role.choices(), default=Role.viewer.value)
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this team member is active or not'
        ,
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
