import builtins
import logging
import os
from pathlib import Path
import signal

from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseServerError
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.shortcuts import redirect
from tracker.forms import AssociateForm
from uploader.boundedexecutor import BoundedExecutor

from uploader.models import FirmwareAnalysis
from dashboard.models import Result
from dashboard.forms import StopAnalysisForm
from porter.views import make_zip


logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def main_dashboard(request):
    if request.user.is_authenticated:
        if FirmwareAnalysis.objects.filter(finished=True, failed=False).count() > 0 and Result.objects.all().count() > 0:
            return render(request, 'dashboard/mainDashboard.html', {'nav_switch': True, 'username': request.user.username})
        messages.info(request, "Redirected - There are no Results to display yet")
        return redirect('embark-uploader-home')
    return HttpResponseForbidden


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
        analysis = form.cleaned_data['analysis']
        logger.info("Stopping analysis with id %s", analysis.id)
        pid = FirmwareAnalysis.objects.get(id=analysis.id).pid
        logger.debug("PID is %s", pid)
        try:
            BoundedExecutor.submit_kill(analysis.id)
            os.killpg(os.getpgid(pid), signal.SIGTERM)  # kill proc group too
            form = StopAnalysisForm()
            form.fields['analysis'].queryset = FirmwareAnalysis.objects.filter(finished=False)
            return render(request, 'dashboard/serviceDashboard.html', {'username': request.user.username, 'form': form, 'success_message': True, 'message': "Stopped successfully"})
        except builtins.Exception as error:
            logger.error("Error %s", error)
            return HttpResponseServerError("Failed to stop process, please handle manually: PID=" + str(pid))
    return HttpResponseBadRequest("invalid form")


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
    form.fields['analysis'].queryset = FirmwareAnalysis.objects.filter(finished=False)
    return render(request, 'dashboard/serviceDashboard.html', {'username': request.user.username, 'form': form, 'success_message': False})


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def report_dashboard(request):
    """
    delivering ReportDashboard with finished_firmwares as dictionary

    :params request: HTTP request

    :return: rendered ReportDashboard
    """
    firmwares = FirmwareAnalysis.objects.all()
    return render(request, 'dashboard/reportDashboard.html', {'firmwares': firmwares, 'username': request.user.username})


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


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def show_log(request, analysis_id):
    """
    renders emba_run.log

    :params request: HTTP request

    :return: rendered emba_run.log
    """
    logger.info("showing log for analyze_id: %s", analysis_id)
    firmware = FirmwareAnalysis.objects.get(id=analysis_id)
    # get the file path
    log_file_path_ = f"{Path(firmware.path_to_logs).parent}/emba_run.log"
    logger.debug("Taking file at %s and render it", log_file_path_)
    try:
        with open(log_file_path_, 'rb') as log_file_:
            return HttpResponse(content=log_file_, content_type="text/plain")
    except FileNotFoundError:
        return HttpResponseServerError(content="File is not yet available")


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def show_logviewer(request, analysis_id):
    """
    renders a log viewer to scroll through emba_run.log

    :params request: HTTP request

    :return: rendered emba_run.log
    """

    logger.info("showing log viewer for analyze_id: %s", analysis_id)
    firmware = FirmwareAnalysis.objects.get(id=analysis_id)
    # get the file path
    log_file_path_ = f"{Path(firmware.path_to_logs).parent}/emba_run.log"
    logger.debug("Taking file at %s and render it", log_file_path_)
    try:
        return render(request, 'dashboard/logViewer.html', {'analysis_id': analysis_id, 'username': request.user.username})

    except FileNotFoundError:
        return HttpResponseServerError(content="File is not yet available")


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def delete_analysis(request, analysis_id):
    """
    :params request: HTTP request
    :params analysis_id: uuid of analysis the user wants to stop

    :return: redirect
    """
    logger.info("Deleting analyze_id: %s", analysis_id)
    analysis = FirmwareAnalysis.objects.get(id=analysis_id)
    # check that the user is authorized
    if request.user == analysis.user or request.user.is_superuser:
        if analysis.finished is False:
            try:
                BoundedExecutor.submit_kill(analysis.id)
                os.killpg(os.getpgid(analysis.pid), signal.SIGTERM)  # kill proc group too
            except builtins.Exception as error:
                logger.error("Error %s when stopping", error)
                messages.error(request, 'Error when stopping Analysis')
        # check if finished
        if analysis.finished is True:
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


@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET"])
def archive_analysis(request, analysis_id):
    """
    archives analysis, safes zip instead of normal log directory
    and sets analysis into archived state
    """
    logger.info("Archiving Analysis with id: %s", analysis_id)
    analysis = FirmwareAnalysis.objects.get(id=analysis_id)
    if analysis.zip_file is None:
        # make archive for uuid
        _ = make_zip(request, analysis_id)
    analysis.do_archive()
    analysis.archived = True
    analysis.save(update_fields=["archived"])
    return redirect('..')
