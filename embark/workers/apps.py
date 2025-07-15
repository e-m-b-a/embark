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

        def reset_dependency_users(**kwargs):
            """
            Reset the 'used_by' field for all DependencyState instances.
            An unexpected shutdown may leave this field populated with workers
            that no longer use the dependency.
            """
            from workers.models import DependencyState  # pylint: disable=import-outside-toplevel
            states = DependencyState.objects.all()
            for state in states:
                state.used_by.clear()
                state.save()
        post_migrate.connect(reset_dependency_users)

        def reset_update_queues(**kwargs):
            """
            Reset the update queues for all workers.
            An unexpected shutdown may leave the update queues
            populated with updates that are no longer relevant.
            """
            from workers.models import Worker, WorkerUpdate  # pylint: disable=import-outside-toplevel
            workers = Worker.objects.all()
            for worker in workers:
                WorkerUpdate.objects.filter(worker__id=worker.id).delete()
        post_migrate.connect(reset_update_queues)
