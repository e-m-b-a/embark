from django import forms
from django.shortcuts import render
import os
import json
import logging
import sys

from django.conf import settings
from django.shortcuts import render
from django.template.context_processors import csrf
from django.template.loader import get_template
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import FileSystemStorage

from .archiver import Archiver

# TODO: Add required headers like type of requests allowed later.


# home page test view TODO: change name accordingly
from .boundedExecutor import BoundedExecutor
from .archiver import Archiver
from .forms import FirmwareForm
from .models import Firmware, FirmwareFile

logger = logging.getLogger('web')


@csrf_exempt
def login(request):
    html_body = get_template('uploader/login.html')
    return HttpResponse(html_body.render())


@csrf_exempt
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


# Function which renders the uploader html
@csrf_exempt
def upload_file(request):

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
                return HttpResponseRedirect("../../home/#uploader")
            else:
                return HttpResponse("queue full")
        else:
            logger.error("Posted Form is unvalid")
            logger.error(form.errors)
            return HttpResponse("Unvalid Form")

    # set available options for firmware
    FirmwareForm.base_fields['firmware'] = forms.ModelChoiceField(queryset=FirmwareFile.objects)
    form = FirmwareForm()
    return render(request, 'uploader/fileUpload.html', {'form': form})


@csrf_exempt
def serviceDashboard(request):
    html_body = get_template('uploader/embaServiceDashboard.html')
    return HttpResponse(html_body.render())


def reportDashboard(request):
    finished_firmwares = Firmware.objects.all().filter(finished=True)
    logger.debug(f"firmwares: \n {finished_firmwares}")
    return render(request, 'uploader/ReportDashboard.html', {'finished_firmwares': finished_firmwares})


# Function which saves the file .
# request - Post request
@csrf_exempt
@require_http_methods(["POST"])
def save_file(request):

    for file in request.FILES.getlist('file'):
        try:
            Archiver.check_extensions(file.name)

            firmware_file = FirmwareFile(file=file)
            firmware_file.save()

            return HttpResponse("Firmwares has been successfully saved")

        except ValueError:
            return HttpResponse("Firmware format not supported")

        except Exception as error:
            return HttpResponse("Firmware could not be uploaded")


def progress(request):
    return render(request, 'uploader/progress.html', context={'text': 'Hello World'})
