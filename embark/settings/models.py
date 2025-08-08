__copyright__ = 'Copyright 2025 The AMOS Projects'
__author__ = 'ashiven, SirGankalot'
__license__ = 'MIT'

from django.db import models


class Settings(models.Model):
    orchestrator = models.BooleanField(
        default=False,
        help_text="Whether the orchestrator is enabled or not"
    )
