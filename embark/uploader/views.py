# pylint: disable=W0613,C0206
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
@require_http_methods(["GET"])
def uploader_home(request):
    if FirmwareFile.objects.all().count() > 0:
        analysis_form = FirmwareAnalysisForm(initial={'firmware': FirmwareFile.objects.latest('upload_date')})
        return render(request, 'uploader/fileUpload.html', {'success_message': False, 'analysis_form': analysis_form})
    return render(request, 'uploader/fileUpload.html')


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
        firmware_file = FirmwareFile.objects.create(file=file)
        firmware_file.save()

    return HttpResponse("successful upload")


@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET", "POST"])
def start_analysis(request):
    """
    View to submit form for flags to run emba with
    if: form is valid
        checks if queue is not full
            starts emba process redirects to uploader page
        else: return Queue full
    else: returns Invalid form error
    Args:
        request: the http req with FirmwareAnalysisForm
    Returns: redirect

    """
    if request.method == 'POST':
        form = FirmwareAnalysisForm(request.POST)
        if form.is_valid():
            logger.debug("Posted Form is valid")
            logger.info("Starting analysis with %s", form.Meta.model.id)

            new_analysis = form.save(commit=False)
            new_analysis.user = request.user
            logger.debug(" FILE_NAME is %s", new_analysis.firmware.file.name)
            new_analysis.firmware_name = new_analysis.firmware.file.name
            new_analysis = form.save()

            # get the id of the firmware-file to submit
            new_firmware_file = FirmwareFile.objects.get(id=new_analysis.firmware.id)
            logger.info("Firmware file: %s", new_firmware_file)

            # inject into bounded Executor
            if BoundedExecutor.submit_firmware(firmware_flags=new_analysis, firmware_file=new_firmware_file):
                return HttpResponseRedirect("/dashboard/service/")
            logger.error("Server Queue full, or other boundenexec error")
            return HttpResponseServerError("Queue full")

    if FirmwareFile.objects.all().count() > 0:
        analysis_form = FirmwareAnalysisForm(initial={'firmware': FirmwareFile.objects.latest('upload_date')})
        return render(request, 'uploader/fileUpload.html', {'success_message': True, 'message': "Successfull upload", 'analysis_form': analysis_form})
    return render(request, 'uploader/fileUpload.html', {'success_message': True, 'message': "Please Upload a File first"})


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
            logger.debug("Form %s is valid", form)

            # get relevant data
            firmware_file = form.cleaned_data['firmware']
            # if firmware_file.user is request.user:
            firmware_file.delete()
            return render(request, 'uploader/firmwareDelete.html', {'success_message': True, 'message': "Successfull delete"})

        logger.error("Form %s is invalid", form)
        logger.error("Form error: %s", form.errors)
        return HttpResponseBadRequest("invalid Form")
    if FirmwareFile.objects.all().count() > 0:
        form = DeleteFirmwareForm(initial={'firmware': FirmwareFile.objects.latest('upload_date').id})
        return render(request, 'uploader/firmwareDelete.html', {'form': form})
    return HttpResponseRedirect('/uploader/')
