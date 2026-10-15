__copyright__ = 'Copyright 2022-2026 Siemens Energy AG'
__author__ = 'Benedikt Kuehne, Eren Erguer'
__license__ = 'MIT'

from http import HTTPStatus
import json
import logging
import os
import shutil
import uuid
import zipfile
from pathlib import Path

from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse, FileResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods

from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import datetime
from django.utils import timezone

from embark.helper import user_is_auth
from uploader.forms import DeviceForm, LabelForm, VendorForm
from uploader.models import FirmwareAnalysis, Label
from porter.exporter import export_results
from porter.models import LogZipFile, AnalysisExport
from porter.forms import FirmwareAnalysisImportForm, FirmwareAnalysisExportForm, DeleteZipForm, RetryImportForm
from porter.tasks import export_analysis as export_analysis_task, import_analysis

logger = logging.getLogger(__name__)
req_logger = logging.getLogger("requests")


def _resolve_import_analysis_id(zip_path):
    """Return the canonical analysis ID stored in an exported archive manifest, if present."""
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            try:
                with archive.open("manifest.json") as manifest_file:
                    manifest = json.load(manifest_file)
            except (KeyError, json.JSONDecodeError):
                return None
    except (zipfile.BadZipFile, OSError):
        return None

    analysis_id = manifest.get("analysis_id")
    if not analysis_id:
        return None

    try:
        return str(analysis_id)
    except (TypeError, ValueError):
        return None


def _prepare_import_batch(analysis_id, archive_path):
    """Create a unique batch directory for the import archive and return its metadata."""
    import_id = uuid.uuid4()    
    if analysis_id:
        import_root = Path(settings.EMBA_LOG_ROOT) / str(analysis_id)
        import_dir = import_root
    else:
        import_root = Path(settings.EMBA_LOG_ROOT)
        import_dir = import_root / str(import_id)

    import_dir.mkdir(parents=True, exist_ok=True)
    files_dir = import_dir
    files_dir.mkdir(parents=True, exist_ok=True)

    source_name = Path(archive_path).name or "import.zip"
    archive_copy = Path(archive_path)

    return str(import_id), str(import_dir), str(archive_copy), str(files_dir)


def _attach_import_label(analysis):
    """Tag imported analyses with the existing label system."""
    if analysis is None:
        return
    label, _ = Label.objects.get_or_create(label_name="imported")
    analysis.label.add(label)


@permission_required('users.porter_permission', login_url='/')
@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET"])
def import_menu(request):
    retry_form = RetryImportForm()
    import_read_form = FirmwareAnalysisImportForm()
    device_form = DeviceForm()
    vendor_form = VendorForm()
    label_form = LabelForm()
    if LogZipFile.objects.all().count() > 0:
        delete_form = DeleteZipForm(initial={'zip-file': LogZipFile.objects.latest('upload_date')})
    else:
        delete_form = DeleteZipForm()
    return render(request, 'porter/import.html', {'import_read_form': import_read_form, 'device_form': device_form, 'vendor_form': vendor_form, 'label_form': label_form, 'delete_form': delete_form, 'retry_form': retry_form})


@permission_required('users.porter_permission', login_url='/')
@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["POST"])
def import_read(request):
    """
    View for importing EMBA analysis(POST only)
    submits file for unpacking via tasks
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
        # check auth
        if not user_is_auth(request.user, zip_file_obj.user):
            logger.error("Permission denied - %s", request)
            messages.error(request, "You don't have permission")
            return redirect('..')
        archive_path = zip_file_obj.file.path
        source_analysis_id = _resolve_import_analysis_id(archive_path)

        if source_analysis_id:
            logger.info("Manifest declares original analysis id %s for archive %s", source_analysis_id, archive_path)
            analysis = FirmwareAnalysis.objects.create(user=request.user)
            analysis.status = dict(analysis.status or {})
            analysis.status.setdefault("source_analysis_id", source_analysis_id)
            analysis.save(update_fields=["status"])
        else:
            analysis = FirmwareAnalysis.objects.create(user=request.user)

        import_id, import_dir, archive_copy, files_dir = _prepare_import_batch(analysis.id, archive_path)
        analysis.status.setdefault("import_id", import_id)
        analysis.status.setdefault("source_analysis_id", source_analysis_id or "")
        analysis.status.setdefault("import_dir", import_dir)
        analysis.status.setdefault("import_files_dir", files_dir)
        analysis.status["import_archive"] = archive_path

        analysis_log_root = Path(settings.EMBA_LOG_ROOT) / str(analysis.id)
        analysis_log_root.mkdir(parents=True, exist_ok=True)
        analysis.path_to_logs = str(analysis_log_root / "emba_logs")
        analysis.path_to_logs = str(Path(analysis.path_to_logs))
        Path(analysis.path_to_logs).mkdir(parents=True, exist_ok=True)
        files_dir = analysis.path_to_logs
        analysis.status["import_files_dir"] = files_dir
        (analysis_log_root / "emba_run.log").touch(exist_ok=True)
        # set device(s), firmware, version, notes
        if form.cleaned_data['firmware'] is not None:
            logger.debug("trying to set firmware for analysis %s", analysis.id)
            analysis.firmware = form.cleaned_data['firmware']
            analysis.firmware_name = os.path.basename(analysis.firmware.file.name)
        if form.cleaned_data['device'] is not None:
            logger.debug("trying to set device(s) for analysis %s", analysis.id)
            analysis.device.set(form.cleaned_data['device'])
        if form.cleaned_data['version'] is not None:
            logger.debug("trying to set version for analysis %s", analysis.id)
            analysis.version = form.cleaned_data['version']
        if form.cleaned_data['notes'] is not None:
            logger.debug("trying to set notes for analysis %s", analysis.id)
            analysis.notes = form.cleaned_data['notes']
        analysis.failed = False
        analysis.zip_file = form.cleaned_data['zip_log_file']
        analysis.finished = False
        analysis.status["import_id"] = import_id
        analysis.status["source_analysis_id"] = source_analysis_id or ""
        analysis.status["import_dir"] = import_dir
        analysis.status["import_files_dir"] = files_dir
        analysis.status["import_archive"] = archive_path  # Pass original path to task
        analysis.status["last_phase"] = "Queued"
        analysis.status["percentage"] = 0
        analysis.status["work"] = True
        analysis.save()
        _attach_import_label(analysis)

        from porter.tasks import _write_import_log_entry
        _write_import_log_entry(analysis, "Queued", 0, "Import queued in dashboard")

        logger.info("Importing analysis with %s", analysis.id)
        if import_analysis.delay(analysis.id, archive_path, files_dir) is not None:
            logger.info("Successfully submitted archive import for %s", analysis.id)
            messages.info(request, 'import submitted for ' + str(analysis.id))
            return redirect('..')
        messages.error(request, 'import failed')
        return redirect('..')
    messages.error(request, 'form invalid')
    return HttpResponseBadRequest("invalid form")


@permission_required('users.porter_permission', login_url='/')
@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["POST"])
def import_save(request):
    """
    File upload(POST)
    type: archive(zip), gets checked by file-extension
    """
    req_logger.info("File upload req by user: %s", request.user)
    logger.info("User %s tryied to upload %s", request.user.username, request.FILES.getlist('file'))
    uploaded_any = False
    for file in request.FILES.getlist('file'):
        # check filetype by extension
        if str(file.name).endswith('.zip'):
            zip_file = LogZipFile.objects.create(file=file)
            zip_file.user = request.user
            zip_file.save()
            uploaded_any = True
        else:
            logger.error("File is not a zip file: %s", file.name)

    if not uploaded_any:
        messages.error(request, "No valid zip file was uploaded")
        return HttpResponseBadRequest("No valid zip file was uploaded")

    messages.info(request, "Successful upload")

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return HttpResponse("successful upload")

    return redirect('..')


@permission_required('users.porter_permission', login_url='/')
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
        # check auth
        if not user_is_auth(request.user, zip_file.user):
            messages.error(request=request, message='Unauthorized')
            return redirect('..')
        zip_file.delete()
        messages.info(request, 'delete successful.')
        return redirect('..')

    logger.error("Form %s is invalid", form)
    logger.error("Form error: %s", form.errors)
    messages.error(request, 'error in form')
    return redirect('..')


@permission_required('users.porter_permission', login_url='/')
@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET"])
def export_menu(request):
    """
    View for export menu.
    """
    export_form = FirmwareAnalysisExportForm()

    exports = AnalysisExport.objects.filter(
        analysis__user=request.user,
    ).select_related(
        "analysis",
    ).order_by(
        "-created_at",
    )

    return render(
        request,
        "porter/export.html",
        {
            "export_form": export_form,
            "exports": exports,
        },
    )

@permission_required('users.porter_permission', login_url='/')
@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["POST"])
def export_analysis(request):
    """
    View for exporting an EMBA analysis.
    """

    req_logger.info(
        "Export request by user: %s",
        request.user,
    )

    form = FirmwareAnalysisExportForm(request.POST)
    if not form.is_valid():
        messages.error(
            request=request,
            message="Form invalid",
        )
        return redirect("..")

    analysis_obj = form.cleaned_data["analysis"]

    if not user_is_auth(
        request.user,
        analysis_obj.user,
    ):
        messages.error(
            request=request,
            message="Unauthorized",
        )
        return redirect("..")

    export_options = form.cleaned_data["export_options"]

    export_analysis_task.delay(
        analysis_obj.id,
        export_options,
    )

    messages.info(
        request=request,
        message="Export started. The ZIP will appear under Available Exports shortly.",
    )

    return redirect("..")


@permission_required('users.porter_permission', login_url='/')
@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET"])
def download_export(request, export_id):
    """
    Download the generated EMBArk export ZIP for an analysis.
    """

    try:
        export = AnalysisExport.objects.select_related("analysis").get(id=export_id)
    except AnalysisExport.DoesNotExist:
        raise Http404("Export does not exist")

    if not user_is_auth(request.user, export.analysis.user):
        return HttpResponseForbidden("You are not authorized!")

    zip_path = (
        Path(export.file_path)
    )

    if not zip_path.is_file():
        raise Http404("Export ZIP does not exist")

    return FileResponse(
        open(zip_path, "rb"),
        as_attachment=True,
        filename=zip_path.name,
    )

@permission_required('users.porter_permission', login_url='/')
@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["POST"])
def delete_export(request, export_id):
    """
    Delete the generated EMBArk export ZIP for an analysis.
    """

    try:
        export = AnalysisExport.objects.select_related("analysis").get(id=export_id)
    except AnalysisExport.DoesNotExist:
        raise Http404("Export does not exist")

    if not user_is_auth(request.user, export.analysis.user):
        return HttpResponseForbidden("You are not authorized!")

    zip_path = (
        Path(export.file_path)
    )

    if zip_path.is_file():
        zip_path.unlink()
        
    export.delete()

    messages.success(
        request,
        f"Export {export.id} deleted.",
    )
    
    return redirect("embark-export-menu")


@permission_required('users.porter_permission', login_url='/')
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
        if user_is_auth(request.user, analysis.user):
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


@permission_required('users.porter_permission', login_url='/')
@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["POST"])
def retry_import(request):
    """
    retry to read emba_log foler with the importer

        returns:
        messages, status
    """
    req_logger.info("%s requested with: %s", __name__, request)
    form = RetryImportForm(request.POST)
    if form.is_valid():
        logger.debug("Posted Form is valid")
        analysis = form.cleaned_data['analysis']
        # check auth
        if not user_is_auth(request.user, analysis.user):
            logger.error("Permission denied - %s", request)
            messages.error(request, "You don't have permission")
            return redirect('..')
        # trying to re-import
        logger.info("Re-importing analysis with %s", analysis.id)
        if analysis.zip_file is None:
            messages.error(request, 'No archive available for re-import')
            return redirect('..')

        archive_path = analysis.zip_file.file.path
        if import_analysis.delay(analysis.id, archive_path) is not None:
            analysis.finished = False
            analysis.failed = False
            analysis.save(update_fields=["finished", "failed"])
            logger.info("Successfully queued re-import for %s", analysis.id)
            messages.info(request, 'import submitted for ' + str(analysis.id))
            return redirect('..')
        messages.error(request, 're-import failed')
        return redirect('..')
    messages.error(request, 'form invalid')
    return HttpResponseBadRequest("invalid form")
