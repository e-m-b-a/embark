__copyright__ = 'Copyright 2022-2025 Siemens Energy AG, Copyright 2023 Christian Bieg'
__author__ = 'Benedikt Kuehne, Christian Bieg'
__license__ = 'MIT'

import builtins
import json
import logging
import os
from pathlib import Path
import signal

from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseServerError, JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.shortcuts import redirect

from embark.helper import user_is_auth
from tracker.forms import AssociateForm
from uploader.boundedexecutor import BoundedExecutor
from uploader.forms import LabelForm
from uploader.models import FirmwareAnalysis, Label
from dashboard.models import Result, SoftwareBillOfMaterial
from dashboard.forms import LabelSelectForm, StopAnalysisForm
from porter.views import make_zip
from users.decorators import require_api_key

from workers.models import Worker
from workers.tasks import stop_remote_analysis


logger = logging.getLogger(__name__)
req_logger = logging.getLogger("requests")


@permission_required("users.dashboard_permission_minimal", login_url='/')
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def main_dashboard(request):
    if FirmwareAnalysis.objects.filter(finished=True, failed=False).count() > 0 and Result.objects.filter(restricted=False).count() > 0:
        return render(request, 'dashboard/mainDashboard.html', {'nav_switch': True, 'username': request.user.username})
    messages.info(request, "Redirected - There are no Results to display yet")
    return redirect('embark-uploader-home')


@permission_required("users.dashboard_permission_advanced", login_url='/')
@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["POST"])
def stop_analysis(request):
    """
    View to submit form for flags to run emba with
    if: form is valid
        send interrupt to analysis.pid
    Args:
        request: the http req with FirmwareForm
    Returns: redirect
    """
    form = StopAnalysisForm(request.POST)
    if form.is_valid():
        logger.debug("Posted Form is valid")
        # get id
        analysis_form = form.cleaned_data['analysis']
        analysis = FirmwareAnalysis.objects.get(id=analysis_form.id)

        if not user_is_auth(request.user, analysis.user):
            return HttpResponseForbidden("You are not authorized!")

        logger.info("Stopping analysis with id %s", analysis.id)

        pid = analysis.pid
        logger.debug("PID is %s", pid)
        try:
            BoundedExecutor.submit_kill(analysis.id)

            if analysis.running_on_worker:
                worker = Worker.objects.get(analysis_id=analysis.id)
                stop_remote_analysis.delay(worker.id)
            else:
                os.killpg(os.getpgid(pid), signal.SIGTERM)  # kill proc group too

            form = StopAnalysisForm()
            form.fields['analysis'].queryset = FirmwareAnalysis.objects.filter(user=request.user).filter(finished=False)

            message = "Analysis termination queued on worker." if analysis.running_on_worker else "Local analysis stopped successfully."
            return render(request, 'dashboard/serviceDashboard.html', {'username': request.user.username, 'form': form, 'success_message': True, 'message': message})

        except Worker.DoesNotExist as exc:
            logger.error("No worker with this analysis has been found: %s", exc)
            analysis.failed = True
            analysis.finished = True
            analysis.save()
            return HttpResponseServerError("No worker with this analysis has been found.")
        except Exception as exc:
            logger.error("Unexpected exception: %s", exc)
            analysis.failed = True
            analysis.save(update_fields=["failed"])
            return HttpResponseServerError("Failed to stop process, but set its status to failed. Please handle EMBA process manually: PID=" + str(pid))

    return HttpResponseBadRequest("invalid form")


@permission_required("users.dashboard_permission_minimal", login_url='/')
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def service_dashboard(request):
    """
    showing running emba analysis
    uses ws/wss for progress
    :params request: req
    :return httpresp: html servicedashboard
    """
    form = StopAnalysisForm()
    form.fields['analysis'].queryset = FirmwareAnalysis.objects.filter(user=request.user).filter(finished=False).exclude(status__work=True)
    return render(request, 'dashboard/serviceDashboard.html', {'username': request.user.username, 'form': form, 'success_message': False})


@permission_required("users.dashboard_permission_minimal", login_url='/')
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def report_dashboard(request):
    """
    delivering ReportDashboard with finished_firmwares as dictionary

    :params request: HTTP request

    :return: rendered ReportDashboard
    """
    # show all not hidden by others and ALL of your own
    firmwares = (FirmwareAnalysis.objects.filter(hidden=False) | FirmwareAnalysis.objects.filter(user=request.user)).distinct()
    label_form = LabelForm()
    label_select_form = LabelSelectForm()
    return render(request, 'dashboard/reportDashboard.html', {'firmwares': firmwares, 'username': request.user.username, 'label_form': label_form, 'label_select_form': label_select_form})


@permission_required("users.dashboard_permission_minimal", login_url='/')
@login_required(login_url='/' + settings.LOGIN_URL)
def individual_report_dashboard(request, analysis_id):
    """
    delivering individualReportDashboard

    :params request id: HTTP request, hashid of the firmware_analysis

    :return: rendered individualReportDashboard of Results for fw_analysis
    """
    logger.info("individual_dashboard - analyze_id: %s", analysis_id)
    form = AssociateForm()
    return render(request, 'dashboard/individualReportDashboard.html', {'username': request.user.username, 'analysis_id': analysis_id, 'form': form})


@permission_required("users.dashboard_permission_advanced", login_url='/')
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def show_log(request, analysis_id):
    """
    renders emba_run.log

    :params request: HTTP request

    :return: rendered emba_run.log
    """
    logger.info("showing log for analyze_id: %s", analysis_id)
    try:
        analysis = FirmwareAnalysis.objects.get(id=analysis_id)
    except FirmwareAnalysis.DoesNotExist:
        analysis = None
        messages.error(request, "Analysis does not exist")
        return redirect('..')
    # check if user auth TODO change to group auth
    if not user_is_auth(request.user, analysis.user):
        return HttpResponseForbidden("You are not authorized!")
    # get the file path
    log_file_path_ = f"{Path(analysis.path_to_logs).parent}/emba_run.log"
    logger.debug("Taking file at %s and render it", log_file_path_)
    try:
        with open(log_file_path_, 'rb') as log_file_:
            return HttpResponse(content=log_file_, content_type="text/plain")
    except FileNotFoundError:
        return HttpResponseServerError(content="File is not yet available")


@permission_required("users.dashboard_permission_advanced", login_url='/')
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def show_error(request, analysis_id):
    """
    renders emba_error.log

    :params request: HTTP request

    :return: rendered emba_error.log
    """
    logger.info("showing emba_error.log for analyze_id: %s", analysis_id)
    try:
        analysis = FirmwareAnalysis.objects.get(id=analysis_id)
    except FirmwareAnalysis.DoesNotExist:
        analysis = None
        messages.error(request, "Analysis does not exist")
        return redirect('..')
    if not user_is_auth(request.user, analysis.user):
        return HttpResponseForbidden("You are not authorized!")
    # get the file path
    log_file_path_ = f"{Path(analysis.path_to_logs).parent}/emba_error.log"
    logger.debug("Taking file at %s and render it", log_file_path_)
    try:
        with open(log_file_path_, 'rb') as log_file_:
            return HttpResponse(content=log_file_, content_type="text/plain")
    except FileNotFoundError:
        return HttpResponseServerError(content="File is not yet available")


@permission_required("users.dashboard_permission_advanced", login_url='/')
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def show_logviewer(request, analysis_id):
    """
    renders a log viewer to scroll through emba_run.log

    :params request: HTTP request

    :return: rendered emba_run.log
    """

    logger.info("showing log viewer for analyze_id: %s", analysis_id)
    try:
        analysis = FirmwareAnalysis.objects.get(id=analysis_id)
    except FirmwareAnalysis.DoesNotExist:
        analysis = None
        messages.error(request, "Analysis does not exist")
        return redirect('..')
    # check if user auth
    if not user_is_auth(request.user, analysis.user):
        messages.error(request, "You are not authorized!")
        return redirect('..')
    # get the file path
    log_file_path_ = f"{Path(analysis.path_to_logs).parent}/emba_run.log"
    if os.path.isfile(log_file_path_):
        if os.path.getsize(log_file_path_) > 10000000:  # bigger than 10MB
            messages.info(request, "The Log is very big, give it some time to open")
        return render(request, 'dashboard/logViewer.html', {'analysis_id': analysis_id, 'username': request.user.username})
    messages.error(request, "File is not yet available")
    return redirect('..')


@permission_required("users.dashboard_permission_advanced", login_url='/')
@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def delete_analysis(request, analysis_id):
    """
    :params request: HTTP request
    :params analysis_id: uuid of analysis the user wants to stop

    :return: redirect
    """
    logger.info("Deleting analyze_id: %s", analysis_id)
    try:
        analysis = FirmwareAnalysis.objects.get(id=analysis_id)
    except FirmwareAnalysis.DoesNotExist:
        analysis = None
        messages.error(request, "Analysis does not exist")
        return redirect('..')
    # check that the user is authorized
    if user_is_auth(request.user, analysis.user):
        if not analysis.finished:
            try:
                BoundedExecutor.submit_kill(analysis.id)
                os.killpg(os.getpgid(analysis.pid), signal.SIGTERM)  # kill proc group too
            except builtins.Exception as error:
                logger.error("Error %s when stopping", error)
                messages.error(request, 'Error when stopping Analysis')
        # check if finished
        if analysis.finished:
            # delete
            try:
                analysis.delete(keep_parents=True)
                messages.success(request, 'Analysis: ' + str(analysis_id) + ' successfully deleted')
            except builtins.Exception as error:
                logger.error("Error %s", error)
                messages.error(request, 'Error when deleting Analysis')
        else:
            messages.error(request, 'Analysis is still running')
        return redirect('..')
    messages.error(request, "You are not authorized to delete another users Analysis")
    return redirect('..')


@permission_required("users.dashboard_permission_minimal", login_url='/')
@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET"])
def archive_analysis(request, analysis_id):
    """
    archives analysis, safes zip instead of normal log directory
    and sets analysis into archived state
    """
    logger.info("Archiving Analysis with id: %s", analysis_id)
    try:
        analysis = FirmwareAnalysis.objects.get(id=analysis_id)
    except FirmwareAnalysis.DoesNotExist:
        analysis = None
        messages.error(request, "Analysis does not exist")
        return redirect('..')
    # check if user auth
    if not user_is_auth(request.user, analysis.user):
        return HttpResponseForbidden("You are not authorized!")
    if analysis.zip_file is None:
        # make archive for uuid
        _ = make_zip(request, analysis_id)
    # TODO is this ever reached??
    analysis.do_archive()
    analysis.archived = True
    analysis.save(update_fields=["archived"])
    messages.success(request, 'Analysis: ' + str(analysis_id) + ' successfully archived')
    return redirect('..')


@permission_required("users.dashboard_permission_advanced", login_url='/')
@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET"])
def hide_analysis(request, analysis_id):
    """
    hides the analysis
    checks user
    """
    logger.info("Hiding Analysis with id: %s", analysis_id)
    try:
        analysis = FirmwareAnalysis.objects.get(id=analysis_id)
    except FirmwareAnalysis.DoesNotExist:
        analysis = None
        messages.error(request, "Analysis does not exist")
        return redirect('..')
    # check if user auth
    if not user_is_auth(request.user, analysis.user):
        return HttpResponseForbidden("You are not authorized!")
    analysis.hidden = True
    analysis.save(update_fields=["hidden"])
    messages.success(request, 'Analysis: ' + str(analysis_id) + ' successfully hidden')
    return redirect('..')


@permission_required("users.dashboard_permission_advanced", login_url='/')
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def create_label(request):
    req_logger.info("User %s called create label", request.user.username)
    form = LabelForm(request.POST)
    if form.is_valid():
        logger.info("User %s tryied to create label %s", request.user.username, request.POST['label_name'])
        new_label = form.save()
        messages.info(request, 'creation successful of ' + str(new_label))
        return redirect('..')
    logger.error("label form invalid %s ", request.POST)
    if 'label_name' in form.errors:
        messages.error(request, 'Label already exists')
    else:
        messages.error(request, 'creation failed.')
    return redirect('..')


@permission_required("users.dashboard_permission_advanced", login_url='/')
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def add_label(request, analysis_id):
    req_logger.info("User %s called add label", request.user.username)
    form = LabelSelectForm(request.POST)
    if form.is_valid():
        new_label = form.cleaned_data["label"]
        logger.info("User %s tryied to add label %s", request.user.username, new_label.label_name)
        # get analysis obj
        try:
            analysis = FirmwareAnalysis.objects.get(id=analysis_id)
        except FirmwareAnalysis.DoesNotExist:
            analysis = None
            messages.error(request, "Analysis does not exist")
            return redirect('..')
        # check auth
        if not user_is_auth(request.user, analysis.user):
            messages.error(request, 'No permissions for this analysis')
            return redirect('..')
        analysis.label.add(new_label)
        analysis.save()
        messages.info(request, 'adding successful of ' + str(new_label))
        return redirect('..')
    logger.error("label form invalid %s ", request.POST)
    messages.error(request, 'Adding Label failed')
    return redirect('..')


@permission_required("users.dashboard_permission_advanced", login_url='/')
@require_http_methods(["POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def rm_label(request, analysis_id, label_name):
    req_logger.info("User %s called rm label", request.user.username)
    logger.info("User %s tryied to rm label %s", request.user.username, label_name)
    # get analysis obj
    try:
        analysis = FirmwareAnalysis.objects.get(id=analysis_id)
    except FirmwareAnalysis.DoesNotExist:
        analysis = None
        messages.error(request, "Analysis does not exist")
        return redirect('..')
    # get lobel obj
    label_obj = Label.objects.get(label_name=label_name)
    # check auth
    if not user_is_auth(request.user, analysis.user):
        messages.error(request, 'Removing Label failed, no permissions')
        return redirect('..')
    analysis.label.remove(label_obj)
    analysis.save()
    messages.info(request, 'removing successful of ' + str(label_name))
    return redirect('..')


@permission_required("users.dashboard_permission_minimal", login_url='/')
@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET"])
def get_sbom(request, sbom_id):
    """
    exports sbom as raw json
    """
    logger.info("getting sbom with id: %s", sbom_id)
    try:
        sbom = SoftwareBillOfMaterial.objects.get(id=sbom_id)
    except SoftwareBillOfMaterial.DoesNotExist:
        sbom = None
        messages.error(request, "SBOM does not exist")
        return redirect('..')
    with open(sbom.file, "r", encoding='UTF-8') as sbom_file:
        response = JsonResponse(json.load(sbom_file))
        response['Content-Disposition'] = 'inline; filename=' + str(sbom_id) + '.json'
        messages.success(request, 'SBOM: ' + str(sbom_id) + ' successfully exported')
        return response


@permission_required("users.dashboard_permission_minimal", login_url='/')
@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET"])
def get_sbom_analysis(request, analysis_id):
    """
    exports sbom as raw json
    """
    logger.info("export sbom with analysis id: %s", analysis_id)
    try:
        analysis = FirmwareAnalysis.objects.get(id=analysis_id)
        result = Result.objects.get(firmware_analysis=analysis)
        sbom = result.sbom
    except Result.DoesNotExist:
        sbom = None
        messages.error(request, "SBOM does not exist")
        return redirect('..')
    # check if user auth
    if not user_is_auth(request.user, analysis.user):
        return HttpResponseForbidden("You are not authorized!")
    if sbom is None:
        messages.error(request, 'Analysis: ' + str(analysis_id) + ' can not find sbom')
        return redirect('..')
    with open(sbom.file, "r", encoding='UTF-8') as sbom_file:
        response = JsonResponse(json.load(sbom_file))
        response['Content-Disposition'] = 'inline; filename=' + str(analysis_id) + '_sbom.json'
        messages.success(request, 'Analysis: ' + str(analysis_id) + ' successfully exported sbom')
        return response


@require_api_key
@require_http_methods(["GET"])
def api_sbom_analysis(request, analysis_id):
    """
    exports sbom as raw json
    """
    logger.info("export sbom with analysis id: %s", analysis_id)
    response = JsonResponse({"ERROR": "SBOM for this analysis-id does not exist"})
    try:
        analysis = FirmwareAnalysis.objects.get(id=analysis_id)
        result = Result.objects.get(firmware_analysis=analysis)
        sbom = result.sbom
    except Result.DoesNotExist:
        response = JsonResponse({"ERROR": "Result for this analysis-id does not exist"})
    # check if user auth
    if not user_is_auth(request.user, analysis.user):
        response = JsonResponse({"ERROR": "You are not authorized!"})
    if sbom is not None:
        with open(sbom.file, "r", encoding='UTF-8') as sbom_file:
            response = JsonResponse(json.load(sbom_file))
            logger.info("export sbom with analysis id: %s", analysis_id)
    response['Content-Disposition'] = 'inline; filename=' + str(analysis_id) + '_sbom.json'
    return response
