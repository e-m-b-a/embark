# pylint: disable=W0613,C0206

from pathlib import Path

import json
import os
import logging

from operator import itemgetter
from http import HTTPStatus

from django.conf import settings
from django.forms import model_to_dict
from django.http.response import Http404
from django.template.loader import get_template
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.urls import reverse

from uploader.archiver import Archiver

from uploader.models import FirmwareAnalysis, ResourceTimestamp
from dashboard.models import Result

logger = logging.getLogger('web')


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def reports(request):
    html_body = get_template('uploader/reports.html')
    return HttpResponse(html_body.render({'username': request.user.username}))


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def html_report(request, analysis_id, html_file):
    report_path = Path(f'{settings.EMBA_LOG_ROOT}{request.path[10:]}')

    if FirmwareAnalysis.objects.filter(id=analysis_id).exists() and FirmwareAnalysis.objects.get(id=analysis_id).user == request.user:
        html_body = get_template(report_path)
        logger.info("html_report - analysis_id: %s html_file: %s", analysis_id, html_file)
        return HttpResponse(html_body.render({'embarkBackUrl': reverse('embark-ReportDashboard')}))
    logger.debug("could  not get template - %s", request)
    return HttpResponseBadRequest


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def html_report_path(request, analysis_id, html_path, html_file):
    report_path = Path(f'{settings.EMBA_LOG_ROOT}{request.path[10:]}')

    if FirmwareAnalysis.objects.get(id=analysis_id).exists() and FirmwareAnalysis.objects.get(id=analysis_id).user == request.user:
        html_body = get_template(report_path)
        logger.info("html_report - analysis_id: %s path: %s html_file: %s", analysis_id, html_path, html_file)
        return HttpResponse(html_body.render({'embarkBackUrl': reverse('embark-ReportDashboard')}))
    logger.debug("could  not get path - %s", request)
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
        result = Result.objects.filter(firmware_analysis=analysis_object)

        logger.debug("getting individual report for %s", result)

        return_dict = dict(model_to_dict(result), **model_to_dict(analysis_object))

        return_dict['name'] = analysis_object.firmware.file.name
        return_dict['strcpy_bin'] = json.loads(return_dict['strcpy_bin'])

        return JsonResponse(data=return_dict, status=HTTPStatus.OK)
    except Result.DoesNotExist:
        logger.error('Report for firmware_id: %s not found in database', analysis_id)
        return JsonResponse(data={'error': 'Not Found'}, status=HTTPStatus.NOT_FOUND)
    except Exception as error:
        logger.error('Report for firmware_id: %s produced error', analysis_id, error)
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
            # logger.info("result-field %s", result[field])
            if result[field] is not None:
                data[field]['sum'] += result[field]

    for field in data:
        if field not in charfields:
            data[field]['mean'] = data[field]['sum'] / data[field]['count']
    data['total_firmwares'] = len(results)
    data['top_entropies'] = [{'name': r.firmware_analysis.firmware.file.name, 'entropy_value': r.entropy_value} for r in
                             top_5_entropies]

    # Taking top 10 most commonly occurring strcpy_bin values
    strcpy_bins = dict(sorted(strcpy_bins.items(), key=itemgetter(1), reverse=True)[:10])
    data['top_strcpy_bins'] = strcpy_bins

    return JsonResponse(data=data, status=HTTPStatus.OK)


@login_required(login_url='/' + settings.LOGIN_URL)
def download_zipped(request, analysis_id):
    """
    download zipped log directory

    :params request: HTTP request
    :params analysis_id: analyzed firmware id

    :return: HttpResponse with zipped log directory on success or HttpResponse including error message
    """

    try:
        firmware = FirmwareAnalysis.objects.get(id=analysis_id)

        if os.path.exists(firmware.path_to_logs):
            archive_path = Archiver.pack(firmware.path_to_logs, 'zip', firmware.path_to_logs, '.')
            logger.debug("Archive %s created", archive_path)
            with open(archive_path, 'rb') as requested_log_dir:
                response = HttpResponse(requested_log_dir.read(), content_type="application/zip")
                response['Content-Disposition'] = 'inline; filename=' + archive_path
                return response

        logger.warning("Firmware with ID: %s does not exist", analysis_id)
        return HttpResponse("Firmware with ID: %s does not exist", analysis_id)

    except FirmwareAnalysis.DoesNotExist as excpt:
        logger.warning("Firmware with ID: %s does not exist in DB", analysis_id)
        logger.warning("Exception: %s", excpt)
        return HttpResponse("Firmware ID does not exist in DB")
    except Exception as error:
        logger.error("Error occured while querying for Firmware object: %s", analysis_id)
        logger.error("Exception: %s", error)
        return HttpResponse("Error occured while querying for Firmware object")


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
