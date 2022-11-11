# pylint: disable=W0613,C0206

from email import message
from pathlib import Path

import json
import os
import logging

from operator import itemgetter
from http import HTTPStatus
from uuid import UUID

from django.conf import settings
from django.forms import model_to_dict
from django.http.response import Http404
from django.shortcuts import redirect
from django.contrib import messages
from django.template.loader import get_template
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from porter.models import LogZipFile
from uploader.boundedexecutor import BoundedExecutor

from uploader.archiver import Archiver

from uploader.models import FirmwareAnalysis, ResourceTimestamp
from dashboard.models import Result

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def reports(request):
    html_body = get_template('uploader/reports.html')
    return HttpResponse(html_body.render({'username': request.user.username}))


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def html_report(request, analysis_id, html_file):
    report_path = Path(f'{settings.EMBA_LOG_ROOT}{request.path[10:]}')
    if FirmwareAnalysis.objects.filter(id=analysis_id).exists():
        analysis = FirmwareAnalysis.objects.get(id=analysis_id)
        if analysis.user == request.user:
            html_body = get_template(report_path)
            logger.debug("html_report - analysis_id: %s html_file: %s", analysis_id, html_file)
            return HttpResponse(html_body.render({'embarkBackUrl': reverse('embark-ReportDashboard')}))
    logger.error("could  not get template - %s", request)
    return HttpResponseBadRequest


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def html_report_path(request, analysis_id, html_path, html_file):
    report_path = Path(f'{settings.EMBA_LOG_ROOT}{request.path[10:]}')
    if FirmwareAnalysis.objects.filter(id=analysis_id).exists():
        analysis = FirmwareAnalysis.objects.get(id=analysis_id)
        if analysis.user == request.user:
            html_body = get_template(report_path)
            logger.debug("html_report - analysis_id: %s path: %s html_file: %s", analysis_id, html_path, html_file)
            return HttpResponse(html_body.render({'embarkBackUrl': reverse('embark-ReportDashboard')}))
    logger.error("could  not get path - %s", request)
    return HttpResponseBadRequest


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def html_report_download(request, analysis_id, html_path, download_file):    # Needed for EMBA?
    base_path = f"{settings.EMBA_LOG_ROOT}"
    if request.path.startswith('/'):
        file_path = request.path[1:]
    else:
        file_path = request.path[2:]
    full_path = os.path.normpath(os.path.join(base_path, file_path))
    if full_path.startswith(base_path):
        with open(full_path, 'rb') as requested_file:
            response = HttpResponse(requested_file.read(), content_type="text/plain")
            response['Content-Disposition'] = 'attachment; filename=' + os.path.basename(full_path)
            logger.info("html_report - analysis_id: %s html_path: %s download_file: %s", analysis_id, html_path,
                        download_file)
            return response
    else:
        response = Http404
        return response


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def html_report_resource(request, analysis_id, img_file):
    content_type = "text/plain"

    if img_file.endswith(".css"):
        content_type = "text/css"
    elif img_file.endswith(".svg"):
        content_type = "image/svg+xml"
    elif img_file.endswith(".png"):
        content_type = "image/png"

    resource_path = Path(f'{settings.EMBA_LOG_ROOT}{request.path[10:]}')
    logger.info("html_report_resource - analysis_id: %s request.path: %s", analysis_id, request.path)

    try:
        # CodeQL issue is not relevant as the urls are defined via urls.py
        with open(resource_path, "rb") as file_:
            return HttpResponse(file_.read(), content_type=content_type)
    except IOError as error:
        logger.error(error)
        logger.error(request.path)

    # just in case -> back to report intro
    report_path = Path(f'{settings.EMBA_LOG_ROOT}{request.path[10:]}')
    html_body = get_template(report_path)
    return HttpResponse(html_body.render())


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def get_individual_report(request, analysis_id):
    """
    Get individual firmware report based on scan id (analysis_id)
    """
    if not analysis_id:
        logger.error('Bad request for get_individual_report')
        return JsonResponse(data={'error': 'Bad request'}, status=HTTPStatus.BAD_REQUEST)
    try:
        analysis_object = FirmwareAnalysis.objects.get(id=analysis_id)
        result = Result.objects.get(firmware_analysis=analysis_object)

        logger.debug("getting individual report for %s", result)

        return_dict = dict(model_to_dict(result))

        return_dict['firmware_name'] = analysis_object.firmware_name
        if analysis_object.firmware:
            return_dict['id'] = analysis_object.firmware.id
        else:
            return_dict['id'] = "Firmware was deleted"
        return_dict['device_list'] = [str(_device) for _device in analysis_object.device.all()]
        return_dict['start_date'] = analysis_object.start_date
        return_dict['end_date'] = analysis_object.end_date
        return_dict['duration'] = analysis_object.duration
        return_dict['notes'] = analysis_object.notes
        return_dict['version'] = analysis_object.version

        return_dict['strcpy_bin'] = json.loads(return_dict['strcpy_bin'])

        return JsonResponse(data=return_dict, status=HTTPStatus.OK)
    except Result.DoesNotExist:
        logger.error('Report for firmware_id: %s not found in database', analysis_id)
        return JsonResponse(data={'error': 'Not Found'}, status=HTTPStatus.NOT_FOUND)


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
            logger.debug("result-field %s", result[field])
            if result[field] is not None:
                if isinstance(result[field], UUID):
                    pass
                else:
                    data[field]['sum'] += result[field]

    for field in data:
        if field not in charfields:
            data[field]['mean'] = data[field]['sum'] / data[field]['count']
    data['total_firmwares'] = len(results)
    data['top_entropies'] = [{'name': r.firmware_analysis.firmware_name, 'entropy_value': r.entropy_value} for r in
                             top_5_entropies]

    # Taking top 10 most commonly occurring strcpy_bin values
    strcpy_bins = dict(sorted(strcpy_bins.items(), key=itemgetter(1), reverse=True)[:10])
    data['top_strcpy_bins'] = strcpy_bins

    return JsonResponse(data=data, status=HTTPStatus.OK)


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def download_zipped(request, analysis_id):
    """
    download zipped log directory

    :params request: HTTP request
    :params analysis_id: analyzed firmware id

    :return: HttpResponse with zipped log directory on success or HttpResponse including error message
    """
    logger.debug("entry download_zipped")
    try:
        firmware = FirmwareAnalysis.objects.get(id=analysis_id)
        # look for LogZipFile
        if firmware.zip_file:
            with open(firmware.zip_file.file.path, 'rb') as requested_log_dir:
                response = HttpResponse(requested_log_dir.read(), content_type="application/zip")
                response['Content-Disposition'] = 'inline; filename=' + firmware.zip_file.file.path
                return response
        logger.error("FirmwareAnalysis with ID: %s does exist, but doesn't have a valid zip in its directory", analysis_id)
        message.error(request, "Logs couldn't be downloaded")
        return redirect('..')

    except FirmwareAnalysis.DoesNotExist as excpt:
        logger.error("Firmware with ID: %s does not exist in DB", analysis_id)
        return HttpResponse("Firmware ID does not exist in DB! How did you get here?")


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def make_zip(request, analysis_id):
    """
    submit analysis for zipping log directory
    """
    try:
        analysis = FirmwareAnalysis.objects.get(id=analysis_id)
        # look for LogZipFile
        if analysis.zip_file is None and analysis.finished is True:
            BoundedExecutor.submit_zip(uuid=analysis_id)
            messages.info(request, "Logs are being zipped")
            return redirect('..')

        messages.error(request, "The Logs are already zipped and ready for downloading")
        return redirect('..')
    except FirmwareAnalysis.DoesNotExist:
        logger.error("Firmware with ID: %s does not exist in DB", analysis_id)
        return HttpResponse("Firmware ID does not exist in DB! How did you get here?")

@require_http_methods(["GET"])
# @login_required(login_url='/' + settings.LOGIN_URL)
def get_load(request):
    """
    JSON request of system-load
    """
    try:
        query_set = ResourceTimestamp.objects.all()
        result = {}
        # for k in model_to_dict(query_set[0]).keys():
        for modelnr in model_to_dict(query_set[0]):
            result[modelnr] = tuple(model_to_dict(querynr)[modelnr] for querynr in query_set)
        return JsonResponse(data=result, status=HTTPStatus.OK)
    except ResourceTimestamp.DoesNotExist:
        logger.error('ResourceTimestamps not found in database')
        return JsonResponse(data={'error': 'Not Found'}, status=HTTPStatus.NOT_FOUND)
