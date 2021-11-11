from pathlib import Path

import json
import os
import logging

from operator import itemgetter
from http import HTTPStatus

from django.conf import settings
# from django import forms
from django.forms import model_to_dict
from django.shortcuts import render     # , redirect
from django.template.loader import get_template
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse # , StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
# from django.views.decorators.cache import cache_control
from django.template import loader

from uploader.boundedexecutor import BoundedExecutor
from uploader.archiver import Archiver
from uploader.forms import FirmwareForm, DeleteFirmwareForm
# from uploader.models import Firmware, FirmwareFile, DeleteFirmware, Result, ResourceTimestamp
from uploader.models import Firmware, FirmwareFile, Result, ResourceTimestamp

logger = logging.getLogger('web')


@csrf_exempt
@require_http_methods(['GET'])
@login_required(login_url='/' + settings.LOGIN_URL)
def check_login(request):
    return HttpResponse('')


@csrf_exempt
def login(request):
    html_body = get_template('uploader/login.html')
    return HttpResponse(html_body.render())


@csrf_exempt
def register(request):
    html_body = get_template('uploader/register.html')
    return HttpResponse(html_body.render())


# TODO @login_required or not?
@csrf_exempt
def logout(request):
    html_body = get_template('uploader/logout.html')
    return HttpResponse(html_body.render())


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
            logger.debug("Archive %s created", archive_path)
            with open(archive_path, 'rb') as requested_log_dir:
                response = HttpResponse(requested_log_dir.read(), content_type="application/zip")
                response['Content-Disposition'] = 'inline; filename=' + archive_path
                return response

        logger.warning("Firmware with ID: %s does not exist", analyze_id)
        return HttpResponse("Firmware with ID: %s does not exist", analyze_id)

    except Firmware.DoesNotExist as ex:
        logger.warning("Firmware with ID: %s does not exist in DB", analyze_id)
        logger.warning("Exception: %s", ex)
        return HttpResponse("Firmware ID does not exist in DB")
    except Exception as ex:
        logger.error("Error occured while querying for Firmware object: %s", analyze_id)
        logger.error("Exception: %s", ex)
        return HttpResponse("Error occured while querying for Firmware object")


@csrf_exempt
@login_required(login_url='/' + settings.LOGIN_URL)
def start_analysis(request, refreshed):
    """
    View to submit form for flags to run emba with
    if: form is valid
        checks if queue is not full
            starts emba process redirects to uploader page
        else: return Queue full
    else: returns Invalid form error
    Args:
        request: the http req
        refreshed: =~id
    Returns:

    """

    # Safely create emba_logs directory
    if request.method == 'POST':
        form = FirmwareForm(request.POST)

        if form.is_valid():
            logger.info("Posted Form is valid")
            firmware_flags = form.save()

            # get relevant data
            # TODO: make clean db access
            firmware_file = FirmwareFile.objects.get(pk=firmware_flags.firmware.pk)

            logger.info("Firmware file: %s", firmware_file)

            # inject into bounded Executor
            if BoundedExecutor.submit_firmware(firmware_flags=firmware_flags, firmware_file=firmware_file):
                if refreshed == 1:
                    return HttpResponseRedirect("../../upload/1/")
                # else:
                return HttpResponseRedirect("../../serviceDashboard/")
            # else:
            return HttpResponse("Queue full")
        # else:
        logger.error("Posted Form is Invalid")
        logger.error(form.errors)
        return HttpResponse("Invalid Form")

    analyze_form = FirmwareForm()
    delete_form = DeleteFirmwareForm()

    if refreshed == 1:
        return render(request, 'uploader/fileUpload.html', {'analyze_form': analyze_form, 'delete_form': delete_form, 'username': request.user.username})
    # else:
    html_body = get_template('uploader/serviceDashboard.html')
    return HttpResponse(html_body.render({'username': request.user.username}))


@csrf_exempt
@login_required(login_url='/' + settings.LOGIN_URL)
def service_dashboard(request):
    html_body = get_template('uploader/serviceDashboard.html')
    return HttpResponse(html_body.render({'username': request.user.username}))


@login_required(login_url='/' + settings.LOGIN_URL)
def report_dashboard(request):
    """
    delivering ReportDashboard with finished_firmwares as dictionary

    :params request: HTTP request

    :return: rendered ReportDashboard
    """

    finished_firmwares = Firmware.objects.all().filter(finished=True)
    return render(request, 'uploader/reportDashboard.html', {'finished_firmwares': finished_firmwares, 'username': request.user.username})


@csrf_exempt
def individual_report_dashboard(request, analyze_id):
    """
    delivering individualReportDashboard

    :params request: HTTP request

    :return: rendered individualReportDashboard
    """
    html_body = get_template('uploader/individualReportDashboard.html')
    logger.info("individual_dashboard - analyze_id: %s", analyze_id)
    return HttpResponse(html_body.render({'username': request.user.username}))


# Function which saves the file .
# request - Post request
@csrf_exempt
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def save_file(request, refreshed):
    """
    file saving on POST requests with attached file

    :params request: HTTP request

    :return: HttpResponse including the status
    """

    for file in request.FILES.getlist('file'):
        try:
            # is_archive = Archiver.check_extensions(file.name)

            # ensure primary key for file saving exists
            firmware_file = FirmwareFile.objects.create()

            # firmware_file.is_archive = is_archive
            # save file in <media-root>/pk/firmware
            firmware_file.file = file
            firmware_file.save()

#             # not used for now since files get stored in different locations
#             firmware_file = FirmwareFile(file=file)
#             if(path.exists(firmware_file.get_abs_path())):
#                 return HttpResponse("File Exists")
#             else:
#                 firmware_file.save()
#                 return HttpResponse("Firmwares has been successfully saved")
#            if is_archive:
            return HttpResponse("Successfully uploaded firmware")
#            else:
#                return HttpResponse("Firmware file not supported by archiver (binary file ?). \n"
#                                    "Use on your own risk.")

        except Exception as error:
            logger.error(error)
            return HttpResponse("Firmware could not be uploaded")


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def get_log(request, log_type, lines):
    """
    View takes a get request with following params:
    1. log_type: selector of log file (daphne, migration, mysql_db, redis_db, uwsgi, web)
    2. lines: lines in log file
    Args:
        request: HTTPRequest instance

    Returns:

    """
    log_file_list = ["daphne", "migration", "mysql_db", "redis_db", "uwsgi", "web"]
    log_file = log_file_list[int(log_type)]
    file_path = f"{settings.BASE_DIR}/logs/{log_file}.log"
    logger.info('Load log file: %s', file_path)
    try:
        with open(file_path) as file_:
            try:
                buffer_ = 500
                lines_found = []
                block_counter = -1

                while len(lines_found) <= lines:
                    try:
                        file_.seek(block_counter * buffer_, 2)
                    except IOError:
                        file_.seek(0)
                        lines_found = file_.readlines()
                        break

                    lines_found = file_.readlines()
                    block_counter -= 1

                result = lines_found[-(lines+1):]
            except Exception as error:
                logger.exception('Wide exception in logstreamer: %s', error)

        return render(request, 'uploader/log.html', {'header': log_file + '.log', 'log': ''.join(result), 'username': request.user.username})
    except IOError:
        return render(request, 'uploader/log.html', {'header': 'Error', 'log': file_path + ' not found!', 'username': request.user.username})


@csrf_exempt
@login_required(login_url='/' + settings.LOGIN_URL)
def home(request):
    html_body = get_template('uploader/mainDashboard.html')
    return HttpResponse(html_body.render({'nav_switch': True, 'username': request.user.username}))


@csrf_exempt
@login_required(login_url='/' + settings.LOGIN_URL)
def main_dashboard(request):
    html_body = get_template('uploader/mainDashboard.html')
    return HttpResponse(html_body.render({'nav_switch': True, 'username': request.user.username}))


@csrf_exempt
# @login_required()#login_url='/' + settings.LOGIN_URL)
def main_dashboard_unauth(request):
    html_body = get_template('uploader/mainDashboard.html')
    return HttpResponse(html_body.render({'nav_switch': False, 'username': request.user.username}))


@csrf_exempt
@login_required(login_url='/' + settings.LOGIN_URL)
def reports(request):
    html_body = get_template('uploader/reports.html')
    return HttpResponse(html_body.render({'username': request.user.username}))


@csrf_exempt
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def html_report(request, analyze_id, html_file):

    report_path = Path(f'/app/emba{request.path}')

    html_body = get_template(report_path)
    logger.info("html_report - analyze_id: %s html_file: %s", analyze_id, html_file)
    return HttpResponse(html_body.render())


@csrf_exempt
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def html_report_resource(request, analyze_id, img_file):

    content_type = "text/plain"

    if img_file.endswith(".css"):
        content_type = "text/css"
    elif img_file.endswith(".svg"):
        content_type = "image/svg+xml"
    elif img_file.endswith(".png"):
        content_type = "image/png"

    resource_path = Path(f'/app/emba{request.path}')
    logger.info("html_report_resource - analyze_id: %s request.path: %s", analyze_id, request.path)

    try:
        # CodeQL issue is not relevant as the urls are defined via urls.py
        with open(resource_path, "rb") as file_:
            return HttpResponse(file_.read(), content_type=content_type)
    except IOError as ex:
        logger.error(ex)
        logger.error(request.path)

    # just in case -> back to report intro
    report_path = Path(f'/app/emba{request.path}')
    html_body = get_template(report_path)
    return HttpResponse(html_body.render())


@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def delete_file(request):
    """
    file deletion on POST requests with attached present firmware file

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

            return HttpResponseRedirect("../../home/upload/1/")

        # else:
        logger.error("Form %s is invalid", form)
        logger.error("Form error: %s", form.errors)
        return HttpResponse("invalid Form")

    return HttpResponseRedirect("../../home/upload/1/")


@csrf_exempt
@require_http_methods(["GET"])
# @login_required(login_url='/' + settings.LOGIN_URL)
def get_load(request):
    try:
        query_set = ResourceTimestamp.objects.all()
        result = {}
        # for k in model_to_dict(query_set[0]).keys():
        for k in model_to_dict(query_set[0]):
            result[k] = tuple(model_to_dict(d)[k] for d in query_set)
        return JsonResponse(data=result, status=HTTPStatus.OK)
    except ResourceTimestamp.DoesNotExist:
        logger.error('ResourceTimestamps not found in database')
        return JsonResponse(data={'error': 'Not Found'}, status=HTTPStatus.NOT_FOUND)


@csrf_exempt
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def get_individual_report(request, analyze_id):
    """
    Get individual firmware report based on scan id (analyze_id)
    """
    firmware_id = analyze_id
    if not firmware_id:
        logger.error('Bad request for get_individual_report')
        return JsonResponse(data={'error': 'Bad request'}, status=HTTPStatus.BAD_REQUEST)
    try:
        result = Result.objects.get(firmware_id=int(firmware_id))
        firmware_object = Firmware.objects.get(pk=int(firmware_id))

        return_dict = dict(model_to_dict(result), **model_to_dict(firmware_object))

        return_dict['name'] = firmware_object.firmware.file.name
        return_dict['strcpy_bin'] = json.loads(return_dict['strcpy_bin'])

        return JsonResponse(data=return_dict, status=HTTPStatus.OK)
    except Result.DoesNotExist:
        logger.error('Report for firmware_id: %s not found in database', firmware_id)
        return JsonResponse(data={'error': 'Not Found'}, status=HTTPStatus.NOT_FOUND)


@csrf_exempt
@require_http_methods(["GET"])
# @login_required(login_url='/' + settings.LOGIN_URL)
def get_accumulated_reports(request):
    """
    Sends accumulated results for main dashboard
    Args:
        request:
    Returns:
        data = {
            'architecture_verified': {'arch_1': count, ....},
            'os_verified': {'os_1': count, .....},
            'all int fields in Result Model': {'sum': float/int, 'count': int, 'mean': float/int}
        }
    """
    results = Result.objects.all()
    top_5_entropies = results.order_by('-entropy_value')[:5]
    charfields = ['architecture_verified', 'os_verified']
    data = {}
    strcpy_bins = {}
    for result in results:
        result = model_to_dict(result)
        # Pop firmware object_id
        result.pop('firmware', None)
        result.pop('emba_command', None)

        # Get counts for all strcpy_bin values
        strcpy_bin = json.loads(result.pop('strcpy_bin', '{}'))
        for key in strcpy_bin:
            if key not in strcpy_bins:
                strcpy_bins[key] = 0
            strcpy_bins[key] += int(strcpy_bin[key])

        for charfield in charfields:
            if charfield not in data:
                data[charfield] = {}

            value = result.pop(charfield)
            if value not in data[charfield]:
                data[charfield][value] = 0
            data[charfield][value] += 1
        for field in result:
            if field not in data:
                data[field] = {'sum': 0, 'count': 0}
            data[field]['count'] += 1
            # logger.info("result-field %s", result[field])
            if result[field] is not None:
                data[field]['sum'] += result[field]

    for field in data:
        if field not in charfields:
            data[field]['mean'] = data[field]['sum']/data[field]['count']
    data['total_firmwares'] = len(results)
    data['top_entropies'] = [{'name': r.firmware.firmware.file.name, 'entropy_value': r.entropy_value} for r in
                             top_5_entropies]

    # Taking top 10 most commonly occurring strcpy_bin values
    strcpy_bins = dict(sorted(strcpy_bins.items(), key=itemgetter(1), reverse=True)[:10])
    data['top_strcpy_bins'] = strcpy_bins

    return JsonResponse(data=data, status=HTTPStatus.OK)
