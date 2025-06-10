from django.apps import AppConfig
from django.db.models.signals import post_migrate


class WorkersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workers'

    def ready(self):
        from workers.tasks import create_periodic_tasks  # pylint: disable=import-outside-toplevel
        post_migrate.connect(create_periodic_tasks)
