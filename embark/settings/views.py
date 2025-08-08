__copyright__ = 'Copyright 2025 The AMOS Projects'
__author__ = 'ashiven, SirGankalot'
__license__ = 'MIT'

from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth import get_user
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, permission_required
from django.conf import settings
from settings.helper import get_settings


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.settings_permission", login_url='/')
def settings_main(request):
    """
    Render the main settings page.
    """
    # the template will only render the settings menu if the user has the is_staff flag set to True
    return render(request, 'settings/index.html', {
        'user': get_user(request),
        'app_settings': get_settings()
    })


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.settings_permission", login_url='/')
def toggle_orchestrator(request):
    """
    Toggle function for orchestrator
    """
    user = get_user(request)
    if not (user.is_staff or user.is_superuser or user.groups.filter(name='Administration_Group').exists()):
        return JsonResponse({"status": "error", "message": "You do not have permission to perform this action."}, status=403)

    app_settings = get_settings()
    app_settings.orchestrator = not app_settings.orchestrator
    app_settings.save()

    return JsonResponse({"status": "success", "enabled": app_settings.orchestrator})
