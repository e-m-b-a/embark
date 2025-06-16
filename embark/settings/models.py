from django.db import models

from users.models import User


class Settings(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    orchestrator = models.BooleanField(
        default=False,
        help_text="Whether the orchestrator is enabled or not"
    )
