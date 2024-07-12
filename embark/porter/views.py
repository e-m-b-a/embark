__copyright__ = 'Copyright 2022-2024 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

from http import HTTPStatus
import logging
import os
from pathlib import Path

from django.http import HttpResponseBadRequest, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages

from uploader.boundedexecutor import BoundedExecutor
from uploader.forms import DeviceForm, LabelForm, VendorForm
from uploader.models import FirmwareAnalysis
from porter.exporter import result_json
from porter.models import LogZipFile
from porter.forms import FirmwareAnalysisImportForm, FirmwareAnalysisExportForm, DeleteZipForm


logger = logging.getLogger(__name__)
req_logger = logging.getLogger("requests")


@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET"])
def import_menu(request):
    import_read_form = FirmwareAnalysisImportForm()
    device_form = DeviceForm()
    vendor_form = VendorForm()
    label_form = LabelForm()
    if LogZipFile.objects.all().count() > 0:
        delete_form = DeleteZipForm(initial={'zip-file': LogZipFile.objects.latest('upload_date')})
    else:
        delete_form = DeleteZipForm()
    return render(request, 'porter/import.html', {'import_read_form': import_read_form, 'device_form': device_form, 'vendor_form': vendor_form, 'label_form': label_form, 'delete_form': delete_form})


@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["POST"])
def import_read(request):
    """
    View for importing EMBA analysis(POST only)
    submits file for unpacking via boundedexecutor
    Args:
        req
    returns:
        messages, status
    """
    req_logger.info("%s requested with: %s", __name__, request)
    form = FirmwareAnalysisImportForm(request.POST)
    if form.is_valid():
        logger.debug("Posted Form is valid")
        zip_file_obj = form.cleaned_data['zip_log_file']
        if zip_file_obj.user != request.user:
            logger.error("Permission denied - %s", request)
            messages.error(request, "You don't have permission")
            return redirect('..')
        # create new analysis
        new_analysis = FirmwareAnalysis.objects.create(user=request.user)
        log_location = f"{settings.EMBA_LOG_ROOT}/{new_analysis.id}"
        log_path = Path(log_location)
        log_path.mkdir(parents=True, exist_ok=True)
        # set device(s), firmware, version, notes
        if form.cleaned_data['firmware'] is not None:
            logger.debug("trying to set firmware for new analysis")
            new_analysis.firmware = form.cleaned_data['firmware']
            new_analysis.firmware_name = os.path.basename(new_analysis.firmware.file.name)
        if form.cleaned_data['device'] is not None:
            logger.debug("trying to set device(s) for new analysis")
            new_analysis.device.set(form.cleaned_data['device'])
        if form.cleaned_data['version'] is not None:
            logger.debug("trying to set version for new analysis")
            new_analysis.version = form.cleaned_data['version']
        if form.cleaned_data['notes'] is not None:
            logger.debug("trying to set notes for new analysis")
            new_analysis.notes = form.cleaned_data['notes']
        new_analysis.failed = False
        new_analysis.zip_file = form.cleaned_data['zip_log_file']
        new_analysis.finished = False
        new_analysis.save()
        logger.info("Importing analysis with %s", new_analysis.id)
        if BoundedExecutor.submit_unzip(uuid=new_analysis.id, file_loc=form.cleaned_data['zip_log_file'].get_abs_path()) is not None:
            # success
            logger.info("Successfully submitted zip for import %s", zip_file_obj)
            messages.info(request, 'import submitted for ' + str(new_analysis.id))
            return redirect('..')
        messages.error(request, 'import failed')
        return redirect('..')
    messages.error(request, 'form invalid')
    return HttpResponseBadRequest("invalid form")


@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["POST"])
def import_save(request):
    """
    File upload(POST)
    type: archive(zip), gets checked by file-extension
    """
    req_logger.info("File upload req by user: %s", request.user)
    logger.info("User %s tryied to upload %s", request.user.username, request.FILES.getlist('file'))
    for file in request.FILES.getlist('file'):
        # check filetype by extension
        if str(file.name).endswith('.zip'):
            zip_file = LogZipFile.objects.create(file=file)
            zip_file.user = request.user
            zip_file.save()
        logger.error("File is not a zip file!")
    messages.info(request, "Successful upload")
    return redirect('..')


@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["POST"])
def import_delete(request):
    """
    delete form for LogZipFile objects
    zip
    """
    req_logger.info("Zip file delete req by user: %s", request.user)
    form = DeleteZipForm(request.POST)
    if form.is_valid():
        logger.debug("Posted Form is valid")
        zip_file = form.cleaned_data['zip_file']
        logger.info("User %s tryied to delete %s", request.user.username, zip_file)
        zip_file.delete()
        messages.info(request, 'delete successful.')
        return redirect('..')

    logger.error("Form %s is invalid", form)
    logger.error("Form error: %s", form.errors)
    messages.error(request, 'error in form')
    return redirect('..')


@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET"])
def export_menu(request):
    """
    view for export menu(GET)
    """
    export_form = FirmwareAnalysisExportForm()
    return render(request, 'porter/export.html', {'export_form': export_form})


@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["POST"])
def export_analysis(request):
    """
    View for exporting EMBA analysis(POST)
    Args:
        form(obj)
    returns:
        json of result(s)
    """
    req_logger.info("Export Req by user: %s", request.user)
    form = FirmwareAnalysisExportForm(request.POST)
    if form.is_valid():
        logger.debug("Posted Form is valid")
        analysis_obj = form.cleaned_data['analysis']
        response_data = result_json(analysis_obj.id)
        return JsonResponse(data=response_data, status=HTTPStatus.OK)
    messages.error(request=request, message='form invalid')
    return redirect('..')


@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET"])
def make_zip(request, analysis_id):
    """
    submits analysis for archiving
    """
    req_logger.info("Zipping Req by user: %s for analysis %s", request.user, analysis_id)
    try:
        analysis = FirmwareAnalysis.objects.get(id=analysis_id)
        # check that the user is authorized
        if request.user == analysis.user or request.user.is_superuser:
            if BoundedExecutor.submit_zip(uuid=analysis_id) is not None:
                # success
                logger.info("Successfully submitted zip request %s", str(analysis_id))
                messages.info(request, 'Zipping ' + str(analysis_id))
                return redirect('embark-dashboard-service')
            messages.error(request, 'zipping failed, queue full?')
        messages.error(request, 'Not authorized')
    except FirmwareAnalysis.DoesNotExist:
        messages.error(request, 'No analysis with that id found')
    return redirect('embark-ReportDashboard')
