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
    emba_check_form = CheckForm()
    return render(request, 'updater/index.html', {'emba_update_form': emba_update_form, 'emba_check_form': emba_check_form})


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
    form = CheckForm(request.POST)
    if form.is_valid():
        option = form.cleaned_data["option"]
        logger.debug("Got option %d for emba dep check", option)
        # inject into bounded Executor
        if BoundedExecutor.submit_emba_check(option=option):
            messages.info(request, "Checking now")
            return redirect('embark-updater-home')
        logger.error("Server Queue full, or other boundenexec error")
        messages.error(request, 'Queue full')
        return redirect('embark-updater-home')
    logger.error("Form invalid")
    messages.error(request, 'Form invalid')
    return redirect('embark-updater-home')


@csrf_protect
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def update_emba(request):
    """
    updates nvd database for emba

    :params request: HTTP request

    :return: HttpResponse including the status
    """
    req_logger.info("User %s called update_emba", request.user.username)
    form = EmbaUpdateForm(request.POST)
    if form.is_valid():
        logger.info("User %s tryied to update emba", request.user.username)
        option = form.cleaned_data['option']
        # do something with it
        logger.debug("Option was: %s", option)
        for option_ in option:
            if option_ == 'GIT':
                pass
        # TODO change shown version
        messages.info(request, "Updating now")
        return redirect('embark-updater-home')
    logger.error("update form invalid %s with error: %s", request.POST, form.errors)
    messages.error(request, 'update not successful')
    return redirect('embark-updater-home')
