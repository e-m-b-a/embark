import logging

from django.conf import settings
from django.shortcuts import render
from django.template.loader import get_template
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect, HttpResponseServerError
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from uploader.models import FirmwareAnalysis, Device

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def tracker(request):
    if FirmwareAnalysis.objects.filter(finished=True, failed=False).count != 0:
        return render(request=request, template_name='tracker/index.html', context={'username': request.user.username})
    logger.info("no data for the tracker yet - %s", request)
    return render(request=request, template_name='tracker/index.html', context={'username': request.user.username, 'message': "No data"})


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def get_report_for_device(request, device_id):
    if Device.objects.filter(id=device_id).exists():
        device = Device.objects.get(id=device_id)
        render(request=request, template_name='reporter/device.html', context={'username': request.user.username, 'device': device})
    logger.error("device id nonexistent: %s", device_id)
    logger.error("could  not get template - %s", request)
    return HttpResponseBadRequest
