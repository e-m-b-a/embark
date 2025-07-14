from django.apps import AppConfig
from django.db.models.signals import post_migrate


class WorkersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workers'

    def ready(self):
        from workers.tasks import create_periodic_tasks  # pylint: disable=import-outside-toplevel
        post_migrate.connect(create_periodic_tasks)

        def reset_orchestrator(**kwargs):
            """
            Reset the orchestrator to ensure it is in a clean state.
            An unexpected shutdown may leave the orchestrator with dangling workers or tasks.
            """
            from workers.orchestrator import get_orchestrator  # pylint: disable=import-outside-toplevel
            orchestrator = get_orchestrator()
            orchestrator.reset()
        post_migrate.connect(reset_orchestrator)
