import logging
import os
import signal

from django.conf import settings
from django.shortcuts import render
from django.template.loader import get_template
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect, HttpResponseServerError, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from uploader.boundedexecutor import BoundedExecutor

from uploader.models import FirmwareAnalysis, Device
from .models import Result
from .forms import StopAnalysisForm

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def tracker(request):
    if FirmwareAnalysis.objects != 0:
        html_body = get_template('reporter/tracker.html')
        return HttpResponse(html_body.render({'username': request.user.username}))
    logger.info("no data for the tracker yet - %s", request)
    return HttpResponseRedirect('/uploader/')


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def get_report_for_device(request, device_id):
    if Device.objects.filter(id=device_id).exists():
        device = Device.objects.get(id=device_id)
        html_body = get_template('reporter/device.html')
        return HttpResponse(html_body.render({'username': request.user.username, 'device': device}))
    logger.error("device id nonexistent: %s", device_id)
    logger.error("could  not get template - %s", request)
    return HttpResponseBadRequest


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def main_dashboard(request):
    if request.user.is_authenticated:
        if Result.objects.all().count() > 0:
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
        except Exception as error:
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
    # if FirmwareAnalysis.objects.all().count() > 0:
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
    finished_firmwares = FirmwareAnalysis.objects.filter(failed=False, finished=True)
    return render(request, 'dashboard/reportDashboard.html', {'finished_firmwares': finished_firmwares, 'username': request.user.username})


@login_required(login_url='/' + settings.LOGIN_URL)
def individual_report_dashboard(request, analysis_id):
    """
    delivering individualReportDashboard

    :params request id: HTTP request, hashid of the firmware_analysis

    :return: rendered individualReportDashboard of Results for fw_analysis
    """
    logger.info("individual_dashboard - analyze_id: %s", analysis_id)
    return render(request, 'dashboard/individualReportDashboard.html', {'username': request.user.username, 'analysis_id': analysis_id})
