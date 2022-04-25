# pylint: disable=W0613,C0206
from http.client import HTTPResponse
import logging
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, HttpResponseServerError
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from uploader.boundedexecutor import BoundedExecutor
from uploader.forms import FirmwareAnalysisForm, DeleteFirmwareForm
from uploader.models import FirmwareFile

logger = logging.getLogger('web')

@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET", "POST"])
def uploader_home(request):
    if request.method == 'POST':
        save_file(request)
    return render(request, 'uploader/fileUpload.html', {'nav_switch': False, 'username': request.user.username})


@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def save_file(request):
    """
    file saving on POST requests with attached file

    :params request: HTTP request

    :return: HttpResponse including the status
    """
    logger.info("User %s tryied to upload %s", request.user.username, request.FILES.getlist('file'))
    for file in request.FILES.getlist('file'):      # FIXME determin usecase for multi-file-upload in one request
        try:
            firmware_file = FirmwareFile.objects.create()
            firmware_file.file = file
            firmware_file.user = request.user   # TODO
            firmware_file.save()

        except Exception as error:
            logger.error(error)
            return HttpResponse("Firmware could not be uploaded")
    return render(request, 'uploader/fileUpload.html', {'nav_switch': False, 'firmware': firmware_file, 'username': request.user.username})


@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["POST"])
def start_analysis(request):
    """
    View to submit form for flags to run emba with
    if: form is valid
        checks if queue is not full
            starts emba process redirects to uploader page
        else: return Queue full
    else: returns Invalid form error
    Args:
        request: the http req with FirmwareForm
    Returns: redirect

    """
    form = FirmwareAnalysisForm(request.POST)

    if form.is_valid():
        logger.info("Posted Form is valid")
        logger.info("Starting analysis with %s", form.Meta.model.id)

        # new_firmware = form.save(commit=False)
        # new_firmware.user = request.user
        new_firmware = form.save()

        # get the id of the firmware-file to submit
        new_firmware_file = FirmwareFile.objects.get(id=new_firmware.firmware.id)
        logger.info("Firmware file: %s", new_firmware_file)

        # inject into bounded Executor
        if BoundedExecutor.submit_firmware(firmware_flags=new_firmware, firmware_file=new_firmware_file):
            return HttpResponseRedirect("../../serviceDashboard/")
        logger.error("Server Queue full, or other boundenexec error")
        return HttpResponseServerError("Queue full")

    logger.error("Posted Form is Invalid: %s", form.errors)
    return HttpResponseBadRequest("Invalid Form")


@require_http_methods(["GET", "POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def delete_fw_file(request):
    """
    file deletion on POST requests with attached firmware file

    :params request: HTTP request

    :return: HttpResponse including the status
    """

    if request.method == 'POST':
        form = DeleteFirmwareForm(request.POST)

        if form.is_valid():
            logger.info("Form %s is valid", form)

            # get relevant data
            firmware_file = form.cleaned_data['firmware']
            firmware_file.delete()

            return HTTPResponse("Successfully deleted Firmware")

        logger.error("Form %s is invalid", form)
        logger.error("Form error: %s", form.errors)
        return HttpResponseBadRequest("invalid Form")

    return render(request, 'uploader/firmwareDelete.html')
