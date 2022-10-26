from datetime import datetime
import logging
from zipfile import ZipFile

from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages

from uploader.forms import DeviceForm, LabelForm, VendorForm
from uploader.models import FirmwareAnalysis
from porter.exporter import result_json
from porter.importer import import_log_dir, result_read_in
from porter.models import LogZipFile
from porter.forms import FirmwareAnalysisImportForm, FirmwareAnalysisExportForm


logger = logging.getLogger(__name__)
req_logger = logging.getLogger("requests")


@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET"])
def import_menu(request):
    import_read_form = FirmwareAnalysisImportForm()
    device_form = DeviceForm()
    vendor_form = VendorForm()
    label_form = LabelForm()
    return render(request, 'porter/import.html', {'import_read_form': import_read_form, 'device_form': device_form, 'vendor_form': vendor_form, 'label_form': label_form})


@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["POST"])
def import_read(request):
    """
    View for importing EMBA analysis
    Args:
        TODO
    returns:
        -
    """
    req_logger.info("%s requested with: %s", __name__, request)
    form = FirmwareAnalysisImportForm(request.POST)
    if form.is_valid():
        logger.debug("Posted Form is valid")
        zip_file_obj = form.cleaned_data['zip_log_file']
        if zip_file_obj.user != request.user:
            logger.error("Permission denied - %s", request)
            return redirect('..')
        # create new analysis
        new_analysis = FirmwareAnalysis.objects.create(user = request.user)
        # set device(s), firmware, version, notes
        if form.cleaned_data['firmware'] is not None:
            logger.debug("trying to set firmware for new analysis")
            new_analysis.firmware = form.cleaned_data['firmware']
            new_analysis.firmware_name = new_analysis.firmware.file.name
        if form.cleaned_data['device'] is not None:
            logger.debug("trying to set device(s) for new analysis")
            new_analysis.device = form.cleaned_data['device']
        if form.cleaned_data['version'] is not None:
            logger.debug("trying to set version for new analysis")
            new_analysis.device = form.cleaned_data['version']
        if form.cleaned_data['notes'] is not None:
            logger.debug("trying to set notes for new analysis")
            new_analysis.device = form.cleaned_data['notes']
        new_analysis.save()
        logger.info("Importing analysis with %s", new_analysis.id)
        if import_log_dir(form.cleaned_data['zip_log_file'].get_abs_path(), new_analysis.id):
            zip_file_obj.delete()
            result_obj = result_read_in(new_analysis.id)
            if result_obj is not None:
                # success
                logger.info("Successfully imported log as %s", str(result_obj.pk))
                messages.info(request, 'import successful for ' + str(result_obj.pk))
                return redirect('..')
        messages.error(request, 'import failed')
        return redirect('..')
    messages.error(request, 'form invalid')
    return HttpResponseBadRequest


@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["POST"])
def import_save(request):
    """
    File upload
    type: archive
    """
    req_logger.info("File upload req by user: %s", request.user)
    logger.info("User %s tryied to upload %s", request.user.username, request.FILES.getlist('file'))
    for file in request.FILES.getlist('file'):
        # check filetype by extension
        if str(file.name).endswith('.zip'):
            zip_file = LogZipFile.objects.create(file=file)
            zip_file.user = request.user
            zip_file.save()
        messages.error(request, 'not a zip file')
        return redirect('..')
    return HttpResponse("successful upload")


@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET"])
def export_menu(request):
    """
    views export.html
    """
    export_form = FirmwareAnalysisExportForm()
    return render(request, 'porter/export.html', {'export_form': export_form})  


@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["POST"])
def export_analysis(request):
    """
    View for exporting EMBA analysis
    Args:
        form(obj)
    returns:
        json of result(s)
    """
    req_logger.info("Export Req by user: %s", request.user)
    # TODO analysis id to str or path
    form = FirmwareAnalysisExportForm(request.POST)
    if form.is_valid():
        logger.debug("Posted Form is valid")
        analysis_obj = form.cleaned_data['analysis']
        file_name = str(result_json(analysis_obj.id))
        with open(file_name, 'rb') as response_file:
            response = HttpResponse(content=response_file.read(), content_type="application/json")
            response['Content-Disposition'] = 'inline; filename=' + file_name
        return response
    messages.error(request=request, message='form invalid')
    return redirect('..')
