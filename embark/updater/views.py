import logging
import os

from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseServerError
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_protect
from embark.helper import get_version_strings

from updater.forms import CheckForm, EmbaUpdateForm
from uploader.boundedexecutor import BoundedExecutor

logger = logging.getLogger(__name__)

req_logger = logging.getLogger("requests")

@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET"])
def updater_home(request):
    req_logger.info("User %s called updater_home", request.user.username)
    emba_update_form = EmbaUpdateForm()
    return render(request, 'updater/index.html', {'emba_update_form': emba_update_form})

@csrf_protect
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def check_update(request):
    """
    checks if components are updateable via wss

    :params request: HTTP request

    :return: wss message
    """
    req_logger.info("User %s called check_update", request.user.username)
    # add dep check
    form = CheckForm()
    if form.is_valid():
        option = form.cleaned_data["option"]
        logger.debug("Got option %d for emba dep check", option)
        # inject into bounded Executor
        if BoundedExecutor.submit_emba_check(option=option):
            return HttpResponse("OK")
        logger.error("Server Queue full, or other boundenexec error")
        return HttpResponseServerError("Queue full")
    logger.error("Form invalid")
    messages.error(request, 'Form invalid')
    return redirect('..')
    

    

@csrf_protect
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def update_emba(request):
    """
    update emba via form with 3 options
    submits update alls to boundedexec

    :params request: HTTP request

    :return: HttpResponse including the status
    """
    req_logger.info("User %s called update_emba", request.user.username)
    form = EmbaUpdateForm(request.POST)
    if form.is_valid():
        logger.info("User %s tryied to update emba", request.user.username)
        # TODO update emba
        # TODO change shown version
        stable_emba_version, container_version, nvd_version, github_emba_version = get_version_strings()
        messages.info(request, "")
        return redirect('..')
    logger.error("update form invalid %s ", request.POST)
    messages.error(request, 'update not successful')
    return redirect('..')
