# pylint: disable=W0613,C0206
import logging

from django.conf import settings
from django.shortcuts import render
from django.template.loader import get_template
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.contrib.auth.decorators import login_required

from uploader.models import FirmwareAnalysis, Result

logger = logging.getLogger('web')


@login_required(login_url='/' + settings.LOGIN_URL)
def main_dashboard(request):
    if request.user.is_authenticated:
        if Result.objects.all().count() > 0:
            html_body = get_template('dashboard/mainDashboard.html')
            return HttpResponse(html_body.render({'nav_switch': True, 'username': request.user.username}))
        return HttpResponseRedirect('../../uploader/')
    return HttpResponseForbidden

@login_required(login_url='/' + settings.LOGIN_URL)
def service_dashboard(request):
    """
    showing running emba analysis
    uses ws/wss for progress
    :params request: req
    :return httpresp: html servicedashboard
    """
    html_body = get_template('dashboard/serviceDashboard.html')
    return HttpResponse(html_body.render({'username': request.user.username}))


@login_required(login_url='/' + settings.LOGIN_URL)
def report_dashboard(request):
    """
    delivering ReportDashboard with finished_firmwares as dictionary

    :params request: HTTP request

    :return: rendered ReportDashboard
    """

    finished_firmwares = FirmwareAnalysis.objects.all().filter(finished=True)
    return render(request, 'dashboard/reportDashboard.html',
                  {'finished_firmwares': finished_firmwares, 'username': request.user.username})


@login_required(login_url='/' + settings.LOGIN_URL)
def individual_report_dashboard(request, hash_id):
    """
    delivering individualReportDashboard

    :params request hash_id: HTTP request, hashid of the firmware_analysis

    :return: rendered individualReportDashboard of Results for fw_analysis
    """
    html_body = get_template('dashboard/individualReportDashboard.html')
    logger.info("individual_dashboard - analyze_id: %s", hash_id)
    return HttpResponse(html_body.render({'username': request.user.username}))
