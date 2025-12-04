__copyright__ = 'Copyright 2025 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

import logging
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, HttpResponseServerError
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.shortcuts import redirect

from embark.helper import disk_space_check, get_emba_version
from updater.forms import CheckForm, UpdateForm, UpgradeForm
from uploader.boundedexecutor import BoundedExecutor

logger = logging.getLogger(__name__)

req_logger = logging.getLogger("requests")


@permission_required("users.updater_permission", login_url='/')
@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET"])
def updater_home(request):
    req_logger.info("User %s called updater_home", request.user.username)
    emba_version, stable_emba_version, container_version, nvd_version, github_emba_version = get_emba_version()
    return render(request, 'updater/index.html', {
        'updater_update_form': UpdateForm(),
        'updater_check_form': CheckForm(),
        'updater_upgrade_form': UpgradeForm(),
        'emba_version': emba_version,
        'stable_emba_version': stable_emba_version,
        'container_version': container_version,
        'nvd_version': nvd_version,
        'github_emba_version': github_emba_version})


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
@staff_member_required
def update_emba(request):
    """
    updates nvd database for emba

    :params request: HTTP request

    :return: HttpResponse including the status
    """
    req_logger.info("User %s called update_emba", request.user.username)
    form = UpdateForm(request.POST)
    if form.is_valid():
        logger.info("User %s tryied to update emba", request.user.username)
        option = form.cleaned_data['option']
        # do something with it
        logger.debug("Option was: %s", option)
        # check if disk space is sufficient
        if not disk_space_check(str(settings.EMBA_ROOT), 20000):
            messages.error(request, 'Disk space is not sufficient for update.')
            return redirect('embark-updater-home')
        logger.debug("Disk space is sufficient for update.")
        for option_ in option:
            # inject into bounded Executor
            if BoundedExecutor.submit_emba_update(option=option_):
                messages.info(request, "Updating now")
                return redirect('embark-updater-home')
            logger.error("Server Queue full, or other boundenexec error")
            messages.error(request, 'Queue full')
            return redirect('embark-updater-home')

        # update version shown on site
        messages.info(request, "Updating now")
        return redirect('embark-updater-home')
    logger.error("update form invalid %s with error: %s", request.POST, form.errors)
    messages.error(request, 'update not successful')
    return redirect('embark-updater-home')


@permission_required("users.updater_permission", login_url='/')
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
@staff_member_required
def upgrade_emba(request):
    """
    upgrade  emba

    :params request: HTTP request

    :return: HttpResponse including the status
    """
    req_logger.info("User %s called update_emba", request.user.username)
    form = UpgradeForm(request.POST)
    if form.is_valid():
        logger.info("User %s tryied to upgrade emba", request.user.username)
        option = form.cleaned_data['option']
        # do something with it
        logger.debug("Option was: %s", option)
        # check if disk space is sufficient
        if not disk_space_check(str(settings.EMBA_ROOT)):
            messages.error(request, 'Disk space is not sufficient for upgrade.')
            return redirect('embark-updater-home')
        logger.debug("Disk space is sufficient for upgrade.")
        for option_ in option:
            # inject into bounded Executor
            if BoundedExecutor.submit_emba_upgrade(option=option_):
                messages.info(request, "Upgrade now")
                return redirect('embark-updater-home')
            logger.error("Server Queue full, or other boundenexec error")
            messages.error(request, 'Queue full')
            return redirect('embark-updater-home')

        # upgrade version shown on site
        messages.info(request, "Upgrading now")
        return redirect('embark-updater-home')
    logger.error("upgrade form invalid %s with error: %s", request.POST, form.errors)
    messages.error(request, 'upgrade not successful')
    return redirect('embark-updater-home')


@permission_required("users.updater_permission", login_url='/')
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
@staff_member_required
def raw_progress(request):
    """
    renders emba_update.log

    :params request: HTTP request

    :return: rendered emba_update.log
    """
    logger.info("showing log for update")
    # get the file path
    log_file_path_ = f"{Path(settings.EMBA_LOG_ROOT)}/emba_update.log"
    logger.debug("Taking file at %s and render it", log_file_path_)
    try:
        with open(log_file_path_, 'rb') as log_file_:
            return HttpResponse(content=log_file_, content_type="text/plain")
    except FileNotFoundError:
        return HttpResponseServerError(content="File is not yet available")
