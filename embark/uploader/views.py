from django import forms
import os
import logging

from django.conf import settings
from django.shortcuts import render
from django.template.context_processors import csrf
from django.template.loader import get_template
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

# TODO: Add required headers like type of requests allowed later.


# home page test view TODO: change name accordingly
from .boundedExecutor import BoundedExecutor
from .archiver import Archiver
from .forms import FirmwareForm, DeleteFirmwareForm
from .models import Firmware, FirmwareFile

logger = logging.getLogger('web')


@csrf_exempt
def login(request):
    html_body = get_template('uploader/login.html')
    return HttpResponse(html_body.render())


@csrf_exempt
@login_required(login_url='/' + settings.LOGIN_URL)
def home(request):
    html_body = get_template('uploader/home.html')
    form = FirmwareForm()
    render(request, 'uploader/fileUpload.html', {'form': form})
    return HttpResponse(html_body.render())


# additional page test view TODO: change name accordingly
def about(request):
    html_body = get_template('uploader/about.html')
    return HttpResponse(html_body.render())


# TODO: have the right trigger, this is just for testing purpose
def download_zipped(request, analyze_id):
    """
    download zipped log directory

    :params request: HTTP request
    :params analyze_id: analyzed firmware id

    :return: HttpResponse with zipped log directory on success or HttpResponse including error message
    """

    try:
        firmware = Firmware.objects.get(pk=analyze_id)

        if os.path.exists(firmware.path_to_logs):
            archive_path = Archiver.pack(firmware.path_to_logs, 'zip', firmware.path_to_logs, '.')
            logger.debug(f"Archive {archive_path} created")
            with open(archive_path, 'rb') as requested_log_dir:
                response = HttpResponse(requested_log_dir.read(), content_type="application/zip")
                response['Content-Disposition'] = 'inline; filename=' + archive_path
                return response

        logger.warning(f"Firmware with ID: {analyze_id} does not exist")
        return HttpResponse(f"Firmware with ID: {analyze_id} does not exist")

    except Firmware.DoesNotExist as ex:
        logger.warning(f"Firmware with ID: {analyze_id} does not exist in DB")
        logger.warning(f"{ex}")
        return HttpResponse(f"Firmware with ID: {analyze_id} does not exist in DB")
    except Exception as ex:
        logger.error(f"Error occured while querying for Firmware object with ID: {analyze_id}")
        logger.warning(f"{ex}")
        return HttpResponse(f"Error occured while querying for Firmware object with ID: {analyze_id}")


@csrf_exempt
@login_required(login_url='/' + settings.LOGIN_URL)
def upload_file(request):
    """
    delivering rendered uploader html

    :params request: HTTP request

    :return: rendered ReportDashboard on success or HttpResponse on failure
    """

    if request.method == 'POST':
        form = FirmwareForm(request.POST)

        if form.is_valid():
            logger.info("Posted Form is valid")
            form.save()

            # get relevant data
            # TODO: make clean db access
            firmware_file = form.cleaned_data['firmware']
            firmware_flags = Firmware.objects.latest('id')

            # inject into bounded Executor
            if BoundedExecutor.submit_firmware(firmware_flags=firmware_flags, firmware_file=firmware_file):
                return HttpResponseRedirect("../../home/upload")
            else:
                return HttpResponse("queue full")
        else:
            logger.error("Posted Form is invalid")
            logger.error(form.errors)
            return HttpResponse("Invalid Form")

    FirmwareForm.base_fields['firmware'] = forms.ModelChoiceField(queryset=FirmwareFile.objects)
    DeleteFirmwareForm.base_fields['firmware'] = forms.ModelChoiceField(queryset=FirmwareFile.objects)

    analyze_form = FirmwareForm()
    delete_form = DeleteFirmwareForm()
    return render(request, 'uploader/fileUpload.html', {'analyze_form': analyze_form, 'delete_form': delete_form})


@csrf_exempt
@login_required(login_url='/' + settings.LOGIN_URL)
def service_dashboard(request):
    html_body = get_template('uploader/embaServiceDashboard.html')
    return HttpResponse(html_body.render())


def report_dashboard(request):
    """
    delivering ReportDashboard with finished_firmwares as dictionary

    :params request: HTTP request

    :return: rendered ReportDashboard
    """

    finished_firmwares = Firmware.objects.all().filter(finished=True)
    logger.debug(f"firmwares: \n {finished_firmwares}")
    return render(request, 'uploader/reportDashboard.html', {'finished_firmwares': finished_firmwares})


# Function which saves the file .
# request - Post request
@csrf_exempt
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def save_file(request):
    """
    file saving on POST requests with attached file

    :params request: HTTP request

    :return: HttpResponse including the status
    """

    for file in request.FILES.getlist('file'):
        try:
            is_archive = Archiver.check_extensions(file.name)

            # ensure primary key for file saving exists
            firmware_file = FirmwareFile(file=file, is_archive=is_archive)
            firmware_file.save()

            # save file in <media-root>/pk/firmware
            firmware_file.file = file
            firmware_file.save()

            if is_archive:
                return HttpResponse("Firmwares has been successfully saved")
            else:
                return HttpResponse("Firmware file not supported by archiver (binary file ?). \n"
                                    "Use on your own risk.")

        except Exception as error:
            logger.error(error)
            return HttpResponse("Firmware could not be uploaded")


@csrf_exempt
def main_dashboard(request):
    html_body = get_template('uploader/mainDashboard.html')
    return HttpResponse(html_body.render())


@csrf_exempt
def reports(request):
    html_body = get_template('uploader/reports.html')
    return HttpResponse(html_body.render())


@require_http_methods(["POST"])
def delete_file(request):
    """
    file deletion on POST requests with attached present firmware file

    :params request: HTTP request

    :return: HttpResponse including the status
    """

    if request.method == 'POST':
        form = DeleteFirmwareForm(request.POST)

        if form.is_valid():
            logger.info(f"Form {form} is valid")

            # get relevant data
            firmware_file = form.cleaned_data['firmware']
            firmware_file.delete()

            return HttpResponseRedirect("../../home/upload")

        else:
            logger.error(f"Form {form} is invalid")
            logger.error(f"{form.errors}")
            return HttpResponse("invalid Form")

    return HttpResponseRedirect("../../home/upload")
