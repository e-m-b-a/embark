# pylint: disable=W0613,C0206
import logging

from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_protect

from uploader.boundedexecutor import BoundedExecutor
from uploader.forms import DeviceForm, FirmwareAnalysisForm, DeleteFirmwareForm, LabelForm, VendorForm
from uploader.models import FirmwareFile

logger = logging.getLogger(__name__)

req_logger = logging.getLogger("requests")


@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET"])
def uploader_home(request):
    if FirmwareFile.objects.all().count() > 0:
        analysis_form = FirmwareAnalysisForm(initial={'firmware': FirmwareFile.objects.latest('upload_date')})
        device_form = DeviceForm()
        label_form = LabelForm()
        vendor_form = VendorForm()
        return render(request, 'uploader/index.html', {'analysis_form': analysis_form, 'device_form': device_form, 'vendor_form': vendor_form, 'label_form': label_form})
    analysis_form = FirmwareAnalysisForm()
    device_form = DeviceForm()
    label_form = LabelForm()
    vendor_form = VendorForm()
    return render(request, 'uploader/index.html', {'analysis_form': analysis_form, 'device_form': device_form, 'vendor_form': vendor_form, 'label_form': label_form})


@csrf_protect
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
    messages.info(request, 'upload successful.')
    return HttpResponse("successful upload")


@csrf_protect
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def device_setup(request):
    # TODO redirect is static ? change to 200
    form = DeviceForm(request.POST)
    if form.is_valid():
        logger.info("User %s tryied to create device", request.user.username)

        new_device = form.save(commit=False)
        new_device.device_user = request.user
        new_device = form.save()

        messages.info(request, 'creation successful of ' + str(new_device))
        return redirect('..')
    logger.error("device form invalid %s ", request.POST)
    messages.error(request, 'creation failed.')
    return redirect('..')


@csrf_protect
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def vendor(request):
    form = VendorForm(request.POST)
    if form.is_valid():
        logger.info("User %s tryied to create vendor %s", request.user.username, request.POST['vendor_name'])

        new_vendor = form.save(commit=True)

        messages.info(request, 'creation successful of ' + str(new_vendor))
        return redirect('..')
    logger.error("vendor form invalid %s ", request.POST)
    messages.error(request, 'creation failed.')
    return redirect('..')


@csrf_protect
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def label(request):
    form = LabelForm(request.POST)
    if form.is_valid():
        logger.info("User %s tryied to create label %s", request.user.username, request.POST['label_name'])

        new_label = form.save(commit=True)

        messages.info(request, 'creation successful of' + str(new_label))
        return redirect('..')
    logger.error("label form invalid %s ", request.POST)
    messages.error(request, 'creation failed.')
    return redirect('..')


@csrf_protect
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
                return redirect('embark-dashboard-service')
            logger.error("Server Queue full, or other boundenexec error")
            return HttpResponseServerError("Queue full")
        logger.error("Form invalid %s", request.POST)
        return HttpResponseBadRequest("Bad Request")
    if FirmwareFile.objects.all().count() > 0:
        analysis_form = FirmwareAnalysisForm(initial={'firmware': FirmwareFile.objects.latest('upload_date')})
        return render(request, 'uploader/index.html', {'analysis_form': analysis_form})
    analysis_form = FirmwareAnalysisForm()
    device_form = DeviceForm()
    return render(request, 'uploader/index.html', {'analysis_form': analysis_form, 'device_form': device_form})


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def manage_file(request):
    if FirmwareFile.objects.all().count() > 0:
        form = DeleteFirmwareForm(initial={'firmware': FirmwareFile.objects.latest('upload_date').id})
        return render(request, 'uploader/manage.html', {'delete_form': form})
    form = DeleteFirmwareForm()
    return render(request, 'uploader/manage.html', {'delete_form': form})


@csrf_protect
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def delete_fw_file(request):
    """
    file deletion on POST requests with attached firmware file

    :params request: HTTP request

    :return: HttpResponse including the status
    """
    form = DeleteFirmwareForm(request.POST)

    if form.is_valid():
        logger.debug("Form %s is valid", form)

        # get relevant data
        firmware_file = form.cleaned_data['firmware']
        # if firmware_file.user is request.user:
        firmware_file.delete()
        messages.info(request, 'delete successful.')
        return redirect('..')

    logger.error("Form %s is invalid", form)
    logger.error("Form error: %s", form.errors)
    messages.error(request, 'error in form')
    return redirect('..')
