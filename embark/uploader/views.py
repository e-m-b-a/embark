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


# TODO: Add required headers like type of requests allowed later.


# home page test view TODO: change name accordingly
from . import boundedExecutor
from .archiver import archiver
from .forms import FirmwareForm


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
            logging.info("Posted Form is valid")

            title = form.cleaned_data['version']
            logging.info(title)
            # form.save()
            return HttpResponse("Uploaded")
        else:
            logging.info("Posted Form is unvalid")
            return HttpResponse("Unvalid Form")

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

    fs = FileSystemStorage()
    for file in request.FILES.getlist('file'):
        try:
            real_filename = fs.save(file.name, file)

            archiver.unpack(os.path.join(settings.MEDIA_ROOT, real_filename), settings.MEDIA_ROOT)
            fs.delete(file.name)

            return HttpResponse("Firmwares has been successfully saved")

        except ValueError:
            fs.delete(file.name)
            return HttpResponse("Firmware format not supported")

        except Exception as error:
            return HttpResponse("Firmware could not be uploaded")


def progress(request):
    return render(request, 'uploader/progress.html', context={'text': 'Hello World'})
