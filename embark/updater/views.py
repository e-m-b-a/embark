import logging

from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_protect

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
    # get into the progress.html f"{settings.EMBA_LOG_ROOT}/emba_check.html"
    try:
        with open(f"{settings.EMBA_LOG_ROOT}/emba_check.html", 'r') as in_file_:
            log_content = in_file_.read()
    except FileNotFoundError:
        logger.error('No dep check file exists yet')
        messages.error(request, "There is no dependancy check log yet")
        log_content = "EMPTY"
    return render(request, 'updater/index.html', {'emba_update_form': emba_update_form, 'emba_check_form': emba_check_form, 'log_content': log_content})


@csrf_protect
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
        if option == 'BOTH':
            check_option = 1
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


@csrf_protect
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def progress(request):
    """
    shows the dep check to the user
    """
    return render(request, 'updater/progress.html', {})

@csrf_protect
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def raw_progress(request):
    """
    shows the dep check to the user as raw file
    """
    # TODO
    return render(request, 'updater/progress.html', {})
