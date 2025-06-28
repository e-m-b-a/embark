from settings.helper import workers_enabled


def show_worker_app_processor(request):
    """
    Context processor to determine if the worker app should be shown.
    """
    show_worker_app = workers_enabled()

    return {'show_worker_app': show_worker_app}
