from django import forms
import logging

from django.conf import settings

from django.shortcuts import render
from django.template.loader import get_template
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

import os
import time
from django.http import StreamingHttpResponse
from django.template import loader

# TODO: Add required headers like type of requests allowed later.


# home page test view TODO: change name accordingly
from uploader.boundedExecutor import BoundedExecutor
from uploader.archiver import Archiver
from uploader.forms import FirmwareForm
from uploader.models import Firmware, FirmwareFile

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
                return HttpResponseRedirect("../../home/#uploader")
            else:
                return HttpResponse("queue full")
        else:
            logger.error("Posted Form is unvalid")
            logger.error(form.errors)
            return HttpResponse("Unvalid Form")

    FirmwareForm.base_fields['firmware'] = forms.ModelChoiceField(queryset=FirmwareFile.objects, empty_label='Select firmware')
    # FirmwareForm.base_fields['firmware_Architecture'] = forms.TypedChoiceField(choices=[(None, 'Select architecture of the linux firmware'),('MIPS', 'MIPS'), ('ARM', 'ARM'), ('x86', 'x86'), ('x64', 'x64'), ('PPC', 'PPC')],empty_value='Architecture')
    # .values_list('file_name')

    form = FirmwareForm()
    return render(request, 'uploader/fileUpload.html', {'form': form})


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
            Archiver.check_extensions(file.name)

            firmware_file = FirmwareFile(file=file)
            firmware_file.save()

            return HttpResponse("Firmwares has been successfully saved")

        except ValueError:
            return HttpResponse("Firmware format not supported")

        except Exception as error:
            return HttpResponse("Firmware could not be uploaded")


def log_streamer(request):
    try:
        firmware_id = request.GET.get('id', None)
        from_ = int(request.GET.get('offset', 0))

        if firmware_id is None:
            return False
        try:
            firmware = Firmware.objects.get(id=int(firmware_id))
        except Firmware.DoesNotExist:
            logger.error(f"Firmware with id: {firmware_id}. Does not exist.")
            return False

        file_path = f"/app/emba/{settings.LOG_ROOT}/{firmware.id}/emba.log"
        mtime = os.path.getmtime(file_path)
        with open(file_path) as f:
            start = -int(from_) or -2000
            filestart = True
            while filestart:
                try:
                    f.seek(start, 2)
                    filestart = False
                    result = f.read()
                    last = f.tell()
                    t = loader.get_template('uploader/log.html')
                    yield t.render({"result": result})
                except IOError:
                    start += 50
        reset = 0
        while True:
            newmtime = os.path.getmtime(file_path)
            if newmtime == mtime:
                time.sleep(1)
                reset += 1
                if reset >= 15:
                    yield "<!-- empty -->"
                continue
            mtime = newmtime
            with open(file_path) as f:
                f.seek(last)
                result = f.read()
                if result:
                    t = loader.get_template('uploader/log.html')
                    yield result + "<script>$('html,body').animate(" \
                                   "{ scrollTop: $(document).height() }, 'slow');</script>"
                last = f.tell()
    except Exception as e:
        logger.exception('Wide exception in logstreamer')
        return False


@require_http_methods(["GET"])
def get_logs(request):
    """
    View takes a get request with following params:
    1. id: id for firmware
    2. offset: offset in log file
    Args:
        request: HTTPRequest instance

    Returns:

    """
    generator = log_streamer(request)
    if type(generator) is bool:
        return HttpResponse('Error in Streaming logs')
    response = StreamingHttpResponse(log_streamer(request))
    response['X-Accel-Buffering'] = "no"
    return response
 

@csrf_exempt
def main_dashboard(request):
    html_body = get_template('uploader/mainDashboard.html')
    return HttpResponse(html_body.render())


@csrf_exempt
def reports(request):
    html_body = get_template('uploader/reports.html')
    return HttpResponse(html_body.render())
