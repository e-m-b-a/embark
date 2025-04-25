__copyright__ = 'Copyright 2025 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

import logging
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, HttpResponseServerError
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.shortcuts import redirect

from updater.forms import CheckForm, EmbaUpdateForm
from uploader.boundedexecutor import BoundedExecutor

logger = logging.getLogger(__name__)

req_logger = logging.getLogger("requests")


@permission_required("users.updater_permission", login_url='/')
@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET"])
def updater_home(request):
    req_logger.info("User %s called updater_home", request.user.username)
    emba_update_form = EmbaUpdateForm()
    emba_check_form = CheckForm()
    return render(request, 'updater/index.html', {'emba_update_form': emba_update_form, 'emba_check_form': emba_check_form})


@permission_required("users.updater_permission", login_url='/')
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def check_update(request):
    """
    checks if components are updateable

    :params request: HTTP request

    :return: wss message
    """
    req_logger.info("User %s called check_update", request.user.username)
    # add dep check
    form = CheckForm(request.POST)
    if form.is_valid():
        option = form.cleaned_data["option"]
        check_option = 1
        if option == 'BOTH':
            pass
        elif option == 'CONTAINER':
            check_option = 2
        logger.debug("Got option %d for emba dep check", check_option)
        # inject into bounded Executor
        if BoundedExecutor.submit_emba_check(option=check_option):
            messages.info(request, "Checking now")
            return redirect('embark-updater-home')
        logger.error("Server Queue full, or other boundenexec error")
        messages.error(request, 'Queue full')
        return redirect('embark-updater-home')
    logger.error("Form invalid")
    messages.error(request, 'Form invalid')
    return redirect('embark-updater-home')


@permission_required("users.updater_permission", login_url='/')
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
            # inject into bounded Executor
            if BoundedExecutor.submit_emba_update(option=option_):
                messages.info(request, "Updating now")
                return redirect('embark-updater-home')
            logger.error("Server Queue full, or other boundenexec error")
            messages.error(request, 'Queue full')
            return redirect('embark-updater-home')
    
    
        # TODO change shown version
        messages.info(request, "Updating now")
        return redirect('embark-updater-home')
    logger.error("update form invalid %s with error: %s", request.POST, form.errors)
    messages.error(request, 'update not successful')
    return redirect('embark-updater-home')


@permission_required("users.updater_permission", login_url='/')
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def raw_progress(request):
    """
    renders emba_update.log

    :params request: HTTP request

    :return: rendered emba_update.log
    """
    logger.info("showing log for update")
    # check if user auth TODO change to group auth
    if not request.user.is_staff :
        messages.error(request,"You are not authorized!")
        return redirect("..")
    # get the file path
    log_file_path_ = f"{Path(settings.EMBA_LOG_ROOT)}/emba_update.log"
    logger.debug("Taking file at %s and render it", log_file_path_)
    try:
        with open(log_file_path_, 'rb') as log_file_:
            return HttpResponse(content=log_file_, content_type="text/plain")
    except FileNotFoundError:
        return HttpResponseServerError(content="File is not yet available")
