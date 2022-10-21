from datetime import datetime
import logging
import os
import re
import shutil
from zipfile import ZipFile

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from django.conf import settings
from django.shortcuts import render
from embark.porter.exporter import result_json
from embark.porter.importer import import_log_dir, result_read_in
from embark.porter.models import LogZipFile
from embark.uploader.models import FirmwareAnalysis

from porter.forms import FirmwareAnalysisImportForm, ExportForm


logger = logging.getLogger(__name__)
req_logger = logging.getLogger("requests")

@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET"])
def import_menu(request):
    import_form = FirmwareAnalysisImportForm()
    return render(request, 'porter/index.html', {'import_form': import_form})


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
        # store file into settings.TEMP_DIR
        # create new analysis
            # assoziate device(s)
        logger.info("Importing analysis with %s", form.Meta.model.id)

        new_analysis = FirmwareAnalysis.objects.create()
        new_analysis.user = request.user
        new_analysis.firmware = form.firmware
        new_analysis.firmware_name = new_analysis.firmware.file.name
        # unzip and copy
        if import_log_dir(form.zip_log_file.get_abs_path(), new_analysis.id):
            result_obj = result_read_in()
            #success
            new_analysis.path_to_logs       # TODO form needs uuid of uploaded file
            new_analysis = form.save()
            logger.info("Successfully imported log as %s", result_obj)
            # TODO return redirect with message


@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["POST"])
def import_save (request):
    """
    File upload
    type: archive
    """
    req_logger.info("File upload req by user: %s", request.user)
    logger.info("User %s tryied to upload %s", request.user.username, request.FILES.getlist('file'))
    for file in request.FILES.getlist('file'):
        zip_file = LogZipFile.objects.create(file=file)
        zip_file.save()
    return HttpResponse("successful upload")


@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET", "POST"])
def export_analysis(request):
    """
    View for exporting EMBA analysis
    Args:
        form(obj)
    returns:
        zipped emba_log dir
    """
    req_logger.info("Export Req by user: %s", request.user)
    # TODO analysis id to str or path
    if request.method == 'POST':
        form = ExportForm(request.POST)
        if form.is_valid():
            logger.debug("Posted Form is valid")
            analysis_list = form.cleaned_data['analysis']
            zip_file_name = f"EMBArk-export-{datetime.time.now()}.zip"
            for _analysis in analysis_list:
                file_list = []
                file_list.append(result_json(_analysis.id))
                # append zips to response
                with ZipFile(f"{settings.TEMP_DIR}/EMBArk-export-{datetime.time.now()}.zip", 'a') as response_zip:
                    for _file in file_list:
                        response_zip.write(_file)
            with ZipFile(f"{settings.TEMP_DIR}/{zip_file_name}", 'rb') as response_zip:        
                response = HttpResponse(content=response_zip.read(), content_type="application/zip")
                response['Content-Disposition'] = 'inline; filename=' + zip_file_name
            return response
    export_form = ExportForm()
    return render(request, 'porter/export.html', {'export_form': export_form})
