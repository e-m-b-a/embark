from django import forms
from django.shortcuts import render
import os
from os import path
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


# TODO: Add required headers like type of requests allowed later.


# home page test view TODO: change name accordingly
from . import boundedExecutor
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
def start(request):
    html_body = get_template('uploader/about.html')
    if boundedExecutor.submit_firmware("test"):
        return HttpResponse(html_body.render())
    else:
        return HttpResponse("queue full")


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
            if boundedExecutor.submit_firmware(firmware_flags=firmware_flags, firmware_file=firmware_file):
                return HttpResponseRedirect("../../home/#uploader")
            else:
                return HttpResponse("queue full")
        else:
            logger.error("Posted Form is unvalid")
            return HttpResponse("Unvalid Form")

    FirmwareForm.base_fields['firmware'] = forms.ModelChoiceField(queryset=FirmwareFile.objects)
    # .values_list('file_name')
    form = FirmwareForm()
    return render(request, 'uploader/fileUpload.html', {'form': form})


@csrf_exempt
def serviceDashboard(request):
    html_body = get_template('uploader/embaServiceDashboard.html')
    return HttpResponse(html_body.render())


# Function which saves the file .
# request - Post request
@csrf_exempt
@require_http_methods(["POST"])
def save_file(request):

    for file in request.FILES.getlist('file'):
        try:

            Archiver.check_extensions(file.name)

            firmware_file = FirmwareFile(file=file)
            if(path.exists(firmware_file.get_abs_path())):
                return HttpResponse("File Exists")
            else:
                firmware_file.save()
                return HttpResponse("Firmwares has been successfully saved")

        except ValueError:
            return HttpResponse("Firmware format not supported")

        except Exception as error:
            return HttpResponse("Firmware could not be uploaded")


def progress(request):
    return render(request, 'uploader/progress.html', context={'text': 'Hello World'})
