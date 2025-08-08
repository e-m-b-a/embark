__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021-2025 The AMOS Projects, Copyright 2021 Siemens AG'
__author__ = 'Benedikt Kuehne, Maximilian Wagner, p4cx, Garima Chauhan, VAISHNAVI UMESH, m-1-k-3, Ashutosh Singh, \
RaviChandra, diegiesskanne, Vaish1795, ravichandraachanta, uk61elac, YulianaPoliakova, SirGankalot, ClProsser, Luka Dekanozishvili'
__license__ = 'MIT'

import logging
import mimetypes
import os
from wsgiref.util import FileWrapper

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError, QueryDict, StreamingHttpResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.shortcuts import redirect, render
from django.core.files.uploadedfile import UploadedFile
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework import serializers

from embark.helper import disk_space_check, user_is_auth
from uploader.executor import submit_firmware
from uploader.forms import DeviceForm, DownloadFirmwareForm, FirmwareAnalysisForm, DeleteFirmwareForm, LabelForm, VendorForm
from uploader.models import FirmwareFile
from uploader.serializers import FirmwareAnalysisSerializer
from users.decorators import require_api_key


logger = logging.getLogger(__name__)

req_logger = logging.getLogger("requests")


@permission_required("users.uploader_permission_advanced", login_url='/')
@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET"])
def uploader_home(request):
    req_logger.info("User %s called uploader_home", request.user.username)
    if FirmwareFile.objects.filter(user=request.user).count() > 0:
        analysis_form = FirmwareAnalysisForm(initial={'firmware': FirmwareFile.objects.filter(user=request.user).latest('upload_date')})
        device_form = DeviceForm()
        label_form = LabelForm()
        vendor_form = VendorForm()
        return render(request, 'uploader/index.html', {'analysis_form': analysis_form, 'device_form': device_form, 'vendor_form': vendor_form, 'label_form': label_form})
    analysis_form = FirmwareAnalysisForm()
    device_form = DeviceForm()
    label_form = LabelForm()
    vendor_form = VendorForm()
    return render(request, 'uploader/index.html', {'analysis_form': analysis_form, 'device_form': device_form, 'vendor_form': vendor_form, 'label_form': label_form})


@permission_required("users.uploader_permission_minimal", login_url='/')
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def save_file(request):
    """
    file saving on POST requests with attached file

    :params request: HTTP request

    :return: HttpResponse including the status
    """
    req_logger.info("User %s called save_file", request.user.username)
    logger.info("User %s tried to upload %s", request.user.username, request.FILES.getlist('file'))
    for file in request.FILES.getlist('file'):      # FIXME determin usecase for multi-file-upload in one request
        firmware_file = FirmwareFile.objects.create(file=file)
        firmware_file.user = request.user
        firmware_file.save()
    messages.info(request, 'Upload successful.')
    return HttpResponse("successful upload")


class BufferFullException(Exception):
    pass


class UploaderView(APIView):
    parser_classes = [MultiPartParser]

    @require_api_key
    def post(self, request, *args, **kwargs):
        """
        file saving on POST requests with attached file

        :params request: HTTP request

        :return: HttpResponse including the status
        """
        if 'file' not in request.data:
            return Response({'status': 'error', 'message': 'No file provided or wrong key'}, status=400)

        file_obj = request.data['file']

        if not file_obj or not isinstance(file_obj, UploadedFile):
            return Response({'status': 'error', 'message': 'Invalid file provided'}, status=400)

        firmware_file = FirmwareFile.objects.create(file=file_obj)
        firmware_file.user = request.api_user
        firmware_file.save()
        messages.info(request, 'Upload successful.')

        # request.data is immutable
        request_data_copy = dict(request.data)
        request_data_copy["firmware"] = firmware_file.id
        del request_data_copy["file"]

        # serializer.validate_scan_modules is only executed if scan_modules is set
        if "scan_modules" not in request_data_copy:
            request_data_copy["scan_modules"] = []

        # create QueryDict, otherwise defaults are not set
        query_dict = QueryDict('', mutable=True)
        query_dict.update(request_data_copy)

        try:
            analysis_id = start_analysis_serialized(query_dict)
            return Response({'status': 'success', 'id': analysis_id}, status=201)
        except BufferFullException:
            return Response({'status': 'Error: Buffer full'}, status=503)
        except serializers.ValidationError as exception:
            return Response({'status': 'Error: Form invalid', 'errors': exception.detail}, status=400)


def start_analysis_serialized(data):
    serializer = FirmwareAnalysisSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    new_analysis = serializer.save()

    logger.info("Starting analysis with %s", serializer.Meta.model.id)

    new_firmware_file = FirmwareFile.objects.get(id=new_analysis.firmware.id)
    logger.debug("Firmware file: %s", new_firmware_file)

    new_analysis.user = new_firmware_file.user
    logger.debug("FILE_NAME is %s", new_analysis.firmware.file.name)
    new_analysis.firmware_name = os.path.basename(new_analysis.firmware.file.name)

    # add labels from devices FIXME what if device has no label
    devices = serializer.validated_data["device"]
    logger.debug("Got %d devices in this analysis", len(devices))
    for device in devices:
        if device.device_label:
            logger.debug("Adding Label=%s", device.device_label.label_name)
            new_analysis.label.add(device.device_label)

    new_analysis.save()
    logger.debug("new_analysis %s has label: %s", new_analysis, new_analysis.label)

    # inject into bounded Executor
    if not submit_firmware(firmware_analysis=new_analysis, firmware_file=new_firmware_file):
        raise BufferFullException

    return new_analysis.id


@permission_required("users.uploader_permission_advanced", login_url='/')
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def device_setup(request):
    req_logger.info("User %s called device_setup", request.user.username)
    # TODO redirect is static ? change to 200
    form = DeviceForm(request.POST)
    if form.is_valid():
        logger.info("User %s tryied to create device", request.user.username)
        new_device = form.save(commit=False)
        new_device.device_user = request.user
        new_device = form.save()
        messages.info(request, 'Creation successful of ' + str(new_device))
        return redirect('..')
    logger.error("Device form invalid %s ", request.POST)
    if 'device_name' in form.errors:
        messages.error(request, 'Device already exists')
    else:
        messages.error(request, 'Creation failed.')
    return redirect('..')


@permission_required("users.uploader_permission_advanced", login_url='/')
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def vendor(request):
    req_logger.info("User %s called vendor", request.user.username)
    form = VendorForm(request.POST)
    if form.is_valid():
        logger.info("User %s tried to create vendor %s", request.user.username, request.POST['vendor_name'])
        new_vendor = form.save()
        messages.info(request, 'Creation successful of ' + str(new_vendor))
        return redirect('..')
    logger.error("Vendor form invalid %s ", request.POST)
    if 'vendor_name' in form.errors:
        messages.error(request, 'Vendor already exists')
    else:
        messages.error(request, 'creation failed.')
    return redirect('..')


@permission_required("users.uploader_permission_advanced", login_url='/')
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def label(request):
    req_logger.info("User %s called label", request.user.username)
    form = LabelForm(request.POST)
    if form.is_valid():
        logger.info("User %s tried to create label %s", request.user.username, request.POST['label_name'])
        new_label = form.save()
        messages.info(request, 'Creation successful of ' + str(new_label))
        return redirect('..')
    logger.error("Label form invalid %s ", request.POST)
    if 'label_name' in form.errors:
        messages.error(request, 'Label already exists')
    else:
        messages.error(request, 'Creation failed.')
    return redirect('..')


@permission_required("users.uploader_permission_advanced", login_url='/')
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
    req_logger.info("User %s called start_analysis", request.user.username)
    if request.method == 'POST':
        form = FirmwareAnalysisForm(request.POST)
        logger.debug("Form: %s", form.errors)
        if form.is_valid():
            logger.info("Starting analysis with %s", form.Meta.model.id)
            new_analysis = form.save(commit=False)
            # get the id of the firmware-file to submit
            new_firmware_file = FirmwareFile.objects.get(id=new_analysis.firmware.id)
            logger.debug("Firmware file: %s", new_firmware_file)
            if not user_is_auth(request.user, new_firmware_file.user):
                messages.error(request=request, message='Unauthorized')
                return redirect('embark-uploader-home')
            new_analysis.user = new_firmware_file.user
            logger.debug(" FILE_NAME is %s", new_analysis.firmware.file.name)
            new_analysis.firmware_name = os.path.basename(new_analysis.firmware.file.name)
            # check if disk space is sufficient
            if not disk_space_check(str(settings.EMBA_LOG_ROOT), 20000000):     # 20GB in KB
                messages.error(request, 'Disk space is not sufficient for analysis.')
                return redirect('embark-uploader-home')
            logger.debug("Disk space is sufficient for analysis.")
            # save form
            new_analysis = form.save(commit=True)
            # add labels from devices FIXME what if device has no label
            devices = form.cleaned_data["device"]
            logger.debug("Got %d devices in this analysis", devices.count())
            for device in devices:
                if device.device_label:
                    logger.debug("Adding Label=%s", device.device_label.label_name)
                    new_analysis.label.add(device.device_label)
            new_analysis.save()
            logger.debug("new_analysis %s has label: %s", new_analysis, new_analysis.label)
            # inject into bounded Executor
            if submit_firmware(firmware_analysis=new_analysis, firmware_file=new_firmware_file):
                return redirect('embark-dashboard-service')
            logger.error("Server Queue full, or other boundedexec error")
            return HttpResponseServerError("Queue full")
        logger.error("Form invalid %s", request.POST)
        return HttpResponseBadRequest("Bad Request")
    if FirmwareFile.objects.filter(user=request.user).count() > 0:
        analysis_form = FirmwareAnalysisForm(initial={'firmware': FirmwareFile.objects.filter(user=request.user).latest('upload_date')})
        return render(request, 'uploader/index.html', {'analysis_form': analysis_form})
    analysis_form = FirmwareAnalysisForm()
    device_form = DeviceForm()
    label_form = LabelForm()
    vendor_form = VendorForm()
    return render(request, 'uploader/index.html', {'analysis_form': analysis_form, 'device_form': device_form, 'vendor_form': vendor_form, 'label_form': label_form})


@permission_required("users.uploader_permission_advanced", login_url='/')
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def manage_file(request):
    req_logger.info("User %s called manage_file", request.user.username)
    if FirmwareFile.objects.filter(user=request.user).count() > 0:
        delete_form = DeleteFirmwareForm(initial={'firmware': FirmwareFile.objects.filter(user=request.user).latest('upload_date').id})
        download_form = DownloadFirmwareForm(initial={'firmware': FirmwareFile.objects.filter(user=request.user).latest('upload_date').id})
    else:
        delete_form = DeleteFirmwareForm()
        download_form = DownloadFirmwareForm()
    return render(request, 'uploader/manage.html', {'delete_form': delete_form, 'download_form': download_form})


@permission_required("users.uploader_permission_advanced", login_url='/')
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def delete_fw_file(request):
    """
    file deletion on POST requests with attached firmware file

    :params request: HTTP request

    :return: HttpResponse including the status
    """
    req_logger.info("User %s called delete_fw_file", request.user.username)
    form = DeleteFirmwareForm(request.POST)

    if form.is_valid():
        logger.debug("Form %s is valid", form)

        # get relevant data
        firmware_file = form.cleaned_data['firmware']
        if not user_is_auth(request.user, firmware_file.user):
            messages.error(request, 'You are not authorized to delete this firmware file.')
            return redirect('embark-uploader-manage-file')
        firmware_file.delete()
        messages.info(request, 'Delete successful.')
        return redirect('embark-uploader-manage-file')

    logger.error("Form %s is invalid", form)
    logger.error("Form error: %s", form.errors)
    messages.error(request, 'error in form')
    return redirect('embark-uploader-manage-file')


@permission_required("users.uploader_permission_minimal", login_url='/')
@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET"])
def uploader_home_minimal(request):
    req_logger.info("User %s called uploader_home_minimal", request.user.username)
    if FirmwareFile.objects.filter(user=request.user).count() > 0:
        analysis_form = FirmwareAnalysisForm(initial={'firmware': FirmwareFile.objects.filter(user=request.user).latest('upload_date')})
        analysis_form.fields.pop('device')
        return render(request, 'uploader/minimal.html', {'analysis_form': analysis_form})
    analysis_form = FirmwareAnalysisForm()
    analysis_form.fields.pop('device')
    return render(request, 'uploader/minimal.html', {'analysis_form': analysis_form})


@permission_required("users.uploader_permission_advanced", login_url='/')
@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["POST"])
def download_firmware(request):
    """
    Download the firmware file
    """
    req_logger.info("User %s called download_firmware", request.user.username)
    form = DownloadFirmwareForm(request.POST)

    if form.is_valid():
        logger.debug("Form %s is valid", form)

        # get relevant data
        firmware_file = form.cleaned_data['firmware']
        if not user_is_auth(request.user, firmware_file.user):
            messages.error(request, 'You are not authorized to download this firmware file.')
            return redirect('embark-uploader-manage-file')
        file = firmware_file.file.path
        filename = os.path.basename(file)
        chunk_size = 8192
        response = StreamingHttpResponse(
            FileWrapper(
                open(file, "rb"),   # pylint: disable=consider-using-with
                chunk_size,
            ),
            content_type=mimetypes.guess_type(file)[0],
        )
        response["Content-Length"] = os.path.getsize(file)
        response["Content-Disposition"] = f"attachment; filename={filename}"
        return response

    logger.error("Form %s is invalid", form)
    logger.error("Form error: %s", form.errors)
    messages.error(request, 'error in form')
    return redirect('embark-uploader-manage-file')
