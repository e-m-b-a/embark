# pylint: disable=C0206
__copyright__ = 'Copyright 2021-2025 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

from pathlib import Path

import json
import os
import logging

from operator import itemgetter
from http import HTTPStatus
import re
from shutil import move
import codecs
from uuid import UUID

from django.conf import settings
from django.forms import model_to_dict
from django.shortcuts import redirect, render
from django.contrib import messages
from django.template.loader import get_template
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from embark.helper import cleanup_charfield, user_is_auth
from uploader.boundedexecutor import BoundedExecutor

from uploader.models import FirmwareAnalysis, ResourceTimestamp
from dashboard.models import Result

from users.decorators import require_api_key

BLOCKSIZE = 1048576     # for codec change


logger = logging.getLogger(__name__)


@permission_required("users.reporter_permission", login_url='/')
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def reports(request):
    html_body = get_template('uploader/reports.html')
    return HttpResponse(html_body.render({'username': request.user.username}))


@permission_required("users.reporter_permission", login_url='/')
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def html_report(request, analysis_id, html_file):
    """
    Lets the user request any html in the html-report
    Checks: valid filename
    TODO test traversal
    """
    # make sure the html file is valid
    html_file_pattern = re.compile(r'^[\w,\s-]+\.html$')
    report_path = Path(f'{settings.EMBA_LOG_ROOT}/{analysis_id}/emba_logs/html-report/{html_file}')
    if FirmwareAnalysis.objects.filter(id=analysis_id).exists() and bool(re.match(html_file_pattern, html_file)):
        analysis = FirmwareAnalysis.objects.get(id=analysis_id)
        if user_is_auth(request.user, analysis.user):
            if (analysis.hidden and analysis.user == request.user) or request.user.is_superuser:
                html_body = get_template(report_path)
                logger.debug("html_report - analysis_id: %s html_file: %s", analysis_id, html_file)
                return HttpResponse(html_body.render({'embarkBackUrl': reverse('embark-ReportDashboard')}))
        messages.error(request, "User not authorized")
    logger.error("could  not get template - %s", request)
    return redirect("..")


@permission_required("users.reporter_permission", login_url='/')
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def html_report_path(request, analysis_id, html_path, file):
    """
    The functions needs to either serve html files or provide download of files in the subdirs
    Checks: valid filename, path.resolved in correct parent
    """
    # make sure the html file is valid
    file_pattern = re.compile(r'^[\w\.-]+\.(tar.gz|html)$')
    if FirmwareAnalysis.objects.filter(id=analysis_id).exists() and bool(re.match(file_pattern, file)):
        analysis = FirmwareAnalysis.objects.get(id=analysis_id)
        if analysis.user == request.user or (not analysis.hidden and user_is_auth(request.user, analysis.user)):
            resource_path = f'{settings.EMBA_LOG_ROOT}/{analysis_id}/emba_logs/html-report/{html_path}/{file}'
            parent_path = os.path.abspath(f'{settings.EMBA_LOG_ROOT}/{analysis_id}/emba_logs/html-report/')
            if os.path.commonpath([parent_path, resource_path]) == parent_path:
                if file.endswith(".tar.gz"):
                    content_type = "text/plain"
                    try:
                        with open(resource_path, 'rb') as requested_file:
                            response = HttpResponse(requested_file.read(), content_type=content_type)
                            response['Content-Disposition'] = 'attachment; filename=' + requested_file
                            logger.info("html_report - analysis_id: %s html_path: %s download_file: %s", analysis_id, html_path, requested_file)
                            return response
                    except FileNotFoundError:
                        messages.error(request, "File not found on the server")
                        logger.error("Couldn't find %s", resource_path)
                        return redirect("..")

                elif file.endswith(".html"):
                    content_type = "text/html"
                    logger.debug("html_report - analysis_id: %s path: %s html_file: %s", analysis_id, html_path, file)
                    try:
                        return render(request, resource_path, {'embarkBackUrl': reverse('embark-ReportDashboard')}, content_type=content_type)
                    except UnicodeDecodeError as decode_error:
                        logger.error("{%s} with error: %s", resource_path, decode_error)
                        # removes all non utf8 chars from html USING: https://stackoverflow.com/questions/191359/how-to-convert-a-file-to-utf-8-in-python
                        # CodeQL issue is not relevant
                        with codecs.open(resource_path, "r", encoding='latin1') as source_file:
                            with codecs.open(f'{resource_path}.new', "w", "utf-8") as target_file:
                                while True:
                                    contents = source_file.read(BLOCKSIZE)
                                    if not contents:
                                        break
                                    target_file.write(contents)
                        # exchange files
                        move(resource_path, f'{resource_path}.old')
                        move(f'{resource_path}.new', resource_path)
                        logger.debug("Removed problematic char from %s", resource_path)
                        return render(request, resource_path, {'embarkBackUrl': reverse('embark-ReportDashboard')}, content_type=content_type)
                messages.error(request, "Can't server that file")
                logger.error("Server can't handle that file - %s", request)
                return redirect("..")
        messages.error(request, "User not authorized")
        logger.error("User not authorized - %s", request)
        return redirect("..")
    logger.error("could  not get path - %s", request)
    return redirect("..")


@permission_required("users.reporter_permission", login_url='/')
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def html_report_resource(request, analysis_id, img_file):
    """
    Serves all resource files needed by the report
    Chcks: filename validity
    """
    # make sure the html file is valid
    img_file_pattern = re.compile(r'^[\w,\s-]+\.+(css|svg|png)$')
    if bool(re.match(img_file_pattern, img_file)):
        if FirmwareAnalysis.objects.filter(id=analysis_id).exists():
            analysis = FirmwareAnalysis.objects.get(id=analysis_id)
            if analysis.hidden is False or analysis.user == request.user or request.user.is_superuser:
                content_type = "text/plain"

                if img_file.endswith(".css"):
                    content_type = "text/css"
                elif img_file.endswith(".svg"):
                    content_type = "image/svg+xml"
                elif img_file.endswith(".png"):
                    content_type = "image/png"

                resource_path = Path(f'{settings.EMBA_LOG_ROOT}/{analysis_id}/emba_logs/html-report/style/{img_file}')
                logger.info("html_report_resource - analysis_id: %s request.path: %s", analysis_id, request.path)

                try:
                    # CodeQL issue is not relevant as the urls are defined via urls.py
                    with open(resource_path, "rb") as file_:
                        return HttpResponse(file_.read(), content_type=content_type)
                except IOError as error:
                    logger.error(error)
                    logger.error(request.path)
    logger.error("could  not get path - %s", request)
    return redirect("..")


@permission_required("users.reporter_permission", login_url='/')
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def get_individual_report(request, analysis_id):
    """
    Get individual firmware report based on scan id (analysis_id)
    """
    if FirmwareAnalysis.objects.filter(id=analysis_id).exists():
        analysis_object = FirmwareAnalysis.objects.get(id=analysis_id)
        if analysis_object.hidden is False or analysis_object.user == request.user or request.user.is_superuser:
            try:
                result = Result.objects.get(firmware_analysis=analysis_object)

                logger.debug("getting individual report for %s", result)

                return_dict = model_to_dict(instance=result, exclude=['vulnerability'])

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
                return_dict['path_to_logs'] = analysis_object.path_to_logs
                return_dict['strcpy_bin'] = json.loads(return_dict['strcpy_bin'])
                # architecture
                if isinstance(return_dict['architecture_verified'], dict):
                    arch_ = json.loads(return_dict['architecture_verified'])
                    for key_, value_ in arch_.items():
                        return_dict['architecture_verified'] += f"{key_}-{value_} "
                else:
                    return_dict['architecture_verified'] = str(return_dict['architecture_verified'])

                return JsonResponse(data=return_dict, status=HTTPStatus.OK)
            except Result.DoesNotExist:
                logger.error('Report for firmware_id: %s not found in database', analysis_id)
                return JsonResponse(data={'error': 'Not Found'}, status=HTTPStatus.NOT_FOUND)
    logger.error('Bad request for get_individual_report')
    return JsonResponse(data={'error': 'Bad request'}, status=HTTPStatus.BAD_REQUEST)


@permission_required("users.reporter_permission", login_url='/')
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
    charfields = ['os_verified', 'architecture_verified']
    data = {}
    strcpy_bins = {}
    system_bin_dict = {}
    for result in results:
        result = model_to_dict(result)
        # Pop all unnecessary data
        result.pop('vulnerability', None)   # FIXME this is disabled for now
        result.pop('firmware', None)
        result.pop('emba_command', None)
        result.pop('date', None)

        # architecture FIXME
        # architecture = result.pop('architecture_verified', '{}')
        # if isinstance(architecture, dict):
        #     # clean-up for architecture descriptions
        #     for key_, value_ in architecture.items():
        #         if value_.lower() == 'el':
        #             data['architecture_verified'] += f"{key_}-Little Endian "
        #         elif value_.lower() == 'eb':
        #             data['architecture_verified'] += f"{key_}-Big Endian "
        #         else:
        #             data['architecture_verified'] += f"{key_}-{value_} "
        # else:
        #     data['architecture_verified'] = str(architecture)

        # Get counts for all strcpy_bin and system_bin values
        system_bin = json.loads(result.pop('system_bin', '{}'))
        strcpy_bin = json.loads(result.pop('strcpy_bin', '{}'))
        for key in strcpy_bin:
            if key not in strcpy_bins:
                strcpy_bins[key] = 0
            strcpy_bins[key] += int(strcpy_bin[key])
        for key in system_bin:
            if key not in system_bin_dict:
                system_bin_dict[key] = 0
            system_bin_dict[key] += int(system_bin[key])

        # os_verified
        for charfield in charfields:
            charfield = cleanup_charfield(charfield)
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
                elif field in ['cve_critical', 'cve_high', 'cve_medium', 'cve_low']:
                    cve_value = json.loads(result[field])
                    data[field]['sum'] += int(cve_value[0])
                else:
                    data[field]['sum'] += result[field]

    for field in data:
        if field not in charfields:
            data[field]['mean'] = data[field]['sum'] / data[field]['count']
    data['total_firmwares'] = len(results)

    # Taking top 10 most commonly occurring strcpy_bin values
    strcpy_bins = dict(sorted(strcpy_bins.items(), key=itemgetter(1), reverse=True)[:10])
    data['top_strcpy_bins'] = strcpy_bins

    # Taking top 10 occurring system binaries
    system_bin_dict = dict(sorted(system_bin_dict.items(), key=itemgetter(1), reverse=True)[:10])
    data['top_system_bins'] = system_bin_dict

    return JsonResponse(data=data, status=HTTPStatus.OK)


@permission_required("users.reporter_permission", login_url='/')
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def download_zipped(request, analysis_id):
    """
    download zipped log directory

    :params request: HTTP request
    :params analysis_id: analyzed firmware id

    :return: HttpResponse with zipped log directory on success or HttpResponse including error message
    """
    # TODO only user can download zips
    logger.debug("entry download_zipped")
    try:
        firmware = FirmwareAnalysis.objects.get(id=analysis_id)
        # look for LogZipFile
        if firmware.zip_file:
            logger.debug("searching for file here: %s", firmware.zip_file.file)
            with open(firmware.zip_file.file.path, 'rb') as requested_log_dir:
                response = HttpResponse(requested_log_dir.read(), content_type="application/zip")
                response['Content-Disposition'] = 'inline; filename=' + str(firmware.id) + '.zip'
                return response
        logger.error("FirmwareAnalysis with ID: %s does exist, but doesn't have a valid zip in its directory", analysis_id)
        messages.error(request, "Logs couldn't be downloaded")
        return redirect('..')

    except FirmwareAnalysis.DoesNotExist:
        logger.error("Firmware with ID: %s does not exist in DB", analysis_id)
        return HttpResponse("Firmware ID does not exist in DB! How did you get here?")


@permission_required("users.reporter_permission", login_url='/')
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def make_zip(request, analysis_id):
    """
    submit analysis for zipping log directory
    """
    # TODO only user can make zips
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


@permission_required("users.reporter_permission", login_url='/')
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


@require_api_key
@require_http_methods(["GET"])
def status_report(request, analysis_id):
    """
    Gets the status of the analysis.
    If the analysis is not yet finished, returns progress.
    Otherwise triggers the generation of a zip file containing the
    status report. Returns a link to the zip file upon a subsequent refresh.
    """

    def build_download_url():
        return request.build_absolute_uri(
            reverse("embark-download", kwargs={"analysis_id": analysis_id}))

    try:
        analysis = FirmwareAnalysis.objects.get(id=analysis_id)

        # Unauthorized
        if not analysis.user.id == request.api_user.id and not request.api_user.is_superuser:
            response_data = {
                "status": "forbidden",
                "error": "You're not allowed to access this resource.",
            }
            response_status = HTTPStatus.FORBIDDEN

        # Failed
        elif analysis.failed:
            # Queue zip generation
            if not analysis.zip_file:
                make_zip(request, analysis_id)
                response_data = {
                    "status": "failed",
                    "error": (
                        "Analysis failed. The logs are being zipped "
                        "and will soon be ready for download."
                    ),
                }
                response_status = HTTPStatus.CREATED
            else:
                response_data = {
                    "status": "failed",
                    "error": "Analysis failed, but logs are available.",
                    "download_url": build_download_url(),
                }
                response_status = HTTPStatus.OK

        # Running
        elif not analysis.finished:
            response_data = {
                "status": "running",
                "message": f"Analysis has been running since {analysis.start_date}.",
                "completion": f"{analysis.status.get('percentage', 0)}% finished",
            }
            response_status = HTTPStatus.ACCEPTED

        # Finished and succeeded, no zip generated
        elif not analysis.zip_file:
            make_zip(request, analysis_id)
            response_data = {
                "status": "finished",
                "message": (
                    "Analysis finished successfully. "
                    "The logs are being zipped "
                    "and will soon be ready for download."
                ),
            }
            response_status = HTTPStatus.CREATED

        # Zip is generated
        else:
            formatted_time = analysis.duration.split(".")[0]
            response_data = {
                "status": "finished",
                "message": f"Analysis finished successfully in {formatted_time}.",
                "download_url": build_download_url(),
            }
            response_status = HTTPStatus.OK

    except FirmwareAnalysis.DoesNotExist:
        response_data = {
            "status": "error",
            "error": "The analysis with the provided UUID doesn't exist."
        }
        response_status = HTTPStatus.NOT_FOUND

    except Exception as exception:
        logger.error("Error: %s", exception)
        response_data = {
            "status": "error",
            "error": "Internal server error",
        }
        response_status = HTTPStatus.INTERNAL_SERVER_ERROR

    # Return the selected message
    return JsonResponse(response_data, status=response_status)
