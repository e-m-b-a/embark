import logging

from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from uploader.models import FirmwareAnalysis
from .models import Result

logger = logging.getLogger('web')


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def main_dashboard(request):
    if request.user.is_authenticated:
        if Result.objects.all().count() > 0:
            return render(request, 'dashboard/mainDashboard.html', {'nav_switch': True, 'username': request.user.username})
        return HttpResponseRedirect('../../uploader/')
    return HttpResponseForbidden


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def service_dashboard(request):
    """
    showing running emba analysis
    uses ws/wss for progress
    :params request: req
    :return httpresp: html servicedashboard
    """
    return render(request, 'dashboard/serviceDashboard.html', {'username': request.user.username})


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def report_dashboard(request):
    """
    delivering ReportDashboard with finished_firmwares as dictionary

    :params request: HTTP request

    :return: rendered ReportDashboard
    """
    finished_firmwares = FirmwareAnalysis.objects.all().filter(finished=True)
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
