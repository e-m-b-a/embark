from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth import get_user
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, permission_required
from django.conf import settings
from settings.models import Settings


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.settings_permission", login_url='/')
def settings_main(request):
    """
    Render the main settings page.
    """
    user = get_user(request)
    user_settings = Settings.objects.filter(user=user).first()
    if not user_settings:
        user_settings = Settings(user=user)
        user_settings.save()

    return render(request, 'settings/index.html', {
        'user_settings': user_settings
    })


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
@permission_required("users.settings_permission", login_url='/')
def toggle_orchestrator(request):
    """
    Toggle function for orchestrator
    """
    user = get_user(request)
    user_settings = Settings.objects.filter(user=user).first()
    if user_settings:
        user_settings.orchestrator = not user_settings.orchestrator
    else:
        user_settings = Settings(user=user, orchestrator=True)
    user_settings.save()

    return JsonResponse({"status": "success", "enabled": user_settings.orchestrator})
