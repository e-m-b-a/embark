from django.db import models


class Settings(models.Model):
    orchestrator = models.BooleanField(
        default=False,
        help_text="Whether the orchestrator is enabled or not"
    )
