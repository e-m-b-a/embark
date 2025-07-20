__copyright__ = 'Copyright 2025 The AMOS Projects'
__author__ = 'ClProsser'
__license__ = 'MIT'

from settings.models import Settings


def get_settings() -> Settings:
    """
    Fetch or create app settings
    :returns: Settings object
    """
    settings = Settings.objects.first()
    if not settings:
        settings = Settings()
        settings.save()

    return settings


def workers_enabled() -> bool:
    """
    Check if workers are enabled
    :returns: true if enabled
    """
    settings = get_settings()

    return settings.orchestrator
