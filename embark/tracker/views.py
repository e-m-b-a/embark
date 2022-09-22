from datetime import datetime, timedelta
import logging

from django.conf import settings
from django.shortcuts import render
from django.template.loader import get_template
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect, HttpResponseServerError
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import redirect

from uploader.models import FirmwareAnalysis, Device, Vendor
from tracker.tables import SimpleDeviceTable
from tracker.forms import TimeForm

logger = logging.getLogger(__name__)


@require_http_methods(["GET", "POST"])
@login_required(login_url='/' + settings.LOGIN_URL)
def tracker(request):
    if request.method == 'POST':
        form = TimeForm(request.POST)
        if form.is_valid():
            logger.debug("Posted Form is valid")
            date = form.cleaned_data['date']
            queryset = Vendor.objects.all()
            if queryset.count() != 0:
                label_list = [] 
                data = []
                for _vendor in queryset:
                    label_list.append(_vendor.vendor_name)
                    data.append(Device.objects.filter(device_vendor = _vendor, device_date__gte=date).count())
                device_table = SimpleDeviceTable(data = Device.objects.all(), template_name="django_tables2/bootstrap-responsive.html")
                time_form = TimeForm()
                return render(request=request, template_name='tracker/index.html', context={'username': request.user.username, 'table': device_table, 'labels': label_list, 'data': data, 'time_form': time_form})
        logger.error("invalid date form")
        return redirect('..')
    elif request.method == 'GET':
        date = datetime.today() - timedelta(days=7)
        queryset = Vendor.objects.all()
        if queryset.count() != 0:
            label_list = [] 
            data = []
            for _vendor in queryset:
                label_list.append(_vendor.vendor_name)
                data.append(Device.objects.filter(device_vendor = _vendor, device_date__gte=date).count())
            device_table = SimpleDeviceTable(data = Device.objects.all(), template_name="django_tables2/bootstrap-responsive.html")
            time_form = TimeForm()
            return render(request=request, template_name='tracker/index.html', context={'username': request.user.username, 'table': device_table, 'labels': label_list, 'data': data, 'time_form': time_form})
        logger.info("no data for the tracker yet - %s", request)
        return redirect('emba-uploader-home')


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def get_report_for_device(request, device_id):
    if Device.objects.filter(id=device_id).exists():
        device = Device.objects.get(id=device_id)
        render(request=request, template_name='reporter/device.html', context={'username': request.user.username, 'device': device})
    logger.error("device id nonexistent: %s", device_id)
    logger.error("could  not get template - %s", request)
    return HttpResponseBadRequest


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def tracker_time(request, time):
    queryset = Vendor.objects.filter(vendor_date__gte = time)
    if queryset.count() != 0:
        label_list = [] 
        data = []
        for _vendor in queryset:
            label_list.append(_vendor.vendor_name)
            data.append(Device.objects.filter(device_vendor = _vendor).count())
        device_table = SimpleDeviceTable(data = Device.objects.all(), template_name="django_tables2/bootstrap-responsive.html")
        return render(request=request, template_name='tracker/index.html', context={'username': request.user.username, 'table': device_table, 'labels': label_list, 'data': data})