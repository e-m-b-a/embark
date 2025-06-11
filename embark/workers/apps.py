from django.apps import AppConfig
from django.db.models.signals import post_migrate


class WorkersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workers'

    def ready(self):
        from workers.tasks import create_periodic_tasks  # pylint: disable=import-outside-toplevel
        post_migrate.connect(create_periodic_tasks)

        from workers.orchestrator import orchestrator  # pylint: disable=import-outside-toplevel

        def start_orchestrator(**kwargs):
            orchestrator.start()

        # In the orchestrator start method, db queries are made to get the free/busy workers
        # therefore, we need to ensure that the database is ready before starting the orchestrator.
        post_migrate.connect(start_orchestrator)
