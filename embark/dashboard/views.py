import builtins
import logging
import os
from pathlib import Path
import signal

from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect, HttpResponseServerError
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from tracker.forms import AssociateForm
from uploader.boundedexecutor import BoundedExecutor

from uploader.models import FirmwareAnalysis
from dashboard.models import Result
from dashboard.forms import StopAnalysisForm

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def main_dashboard(request):
    if request.user.is_authenticated:
        if FirmwareAnalysis.objects.filter(finished=True, failed=False).count() > 0 and Result.objects.all().count() > 0:
            return render(request, 'dashboard/mainDashboard.html', {'nav_switch': True, 'username': request.user.username})
        return HttpResponseRedirect('../../uploader/')
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
            os.killpg(os.getpgid(pid), signal.SIGTERM)
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

    :params request id: HTTP request, id of the firmware_analysis

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
        with open(log_file_path_, 'r', encoding='utf-8') as log_file_:
            return HttpResponse(content=log_file_, content_type="text/plain")
    except FileNotFoundError:
        return HttpResponseServerError(content="File is not yet available")
