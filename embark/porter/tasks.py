__copyright__ = 'Copyright 2022-2026 Siemens Energy AG'
__author__ = 'Eren Erguer'
__license__ = 'MIT'

import logging
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from porter.exporter import export_results
from porter.importer import import_results
from porter.models import AnalysisExport
from uploader.models import FirmwareAnalysis

logger = logging.getLogger(__name__)


def _local_iso_timestamp():
    """Return timestamps in the app's configured local timezone."""
    return timezone.localtime(timezone.now()).isoformat()


def _write_import_log_entry(analysis, phase, percentage, message):
    """Create the import run log file and append a single progress line."""
    log_root = Path(settings.EMBA_LOG_ROOT) / str(analysis.id)
    log_root.mkdir(parents=True, exist_ok=True)
    log_path = log_root / "emba_run.log"
    log_path.touch(exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{_local_iso_timestamp()} [import] {phase} ({percentage}%) {message}\n")


def _log_import_progress(analysis, phase, percentage, message, task=None):
    """Persist progress to the analysis status JSON and append a log line."""
    status = dict(analysis.status or {})
    status["analysis"] = str(analysis.id)
    status["firmware_name"] = getattr(analysis, "firmware_name", "") or status.get("firmware_name", "")
    status["last_update"] = _local_iso_timestamp()
    status["last_phase"] = phase
    status["phase_list"] = list(dict.fromkeys([*status.get("phase_list", []), phase]))
    status["percentage"] = percentage
    status["work"] = percentage < 100
    status["finished"] = percentage >= 100
    if message:
        status["last_module"] = message
        status["module_list"] = list(dict.fromkeys([*status.get("module_list", []), message]))

    analysis.status = status
    analysis.save(update_fields=["status"])

    if task is not None and getattr(task, "request", None) is not None and getattr(task.request, "id", None):
        task.update_state(state="PROGRESS", meta={
            "analysis_id": str(analysis.id),
            "phase": phase,
            "percentage": percentage,
            "message": message,
        })

    _write_import_log_entry(analysis, phase, percentage, message)


@shared_task(bind=True)
def import_analysis(self, analysis_id, zip_path, extract_root=None):
    """Keep the import lifecycle simple: queued -> running -> failed/completed."""
    analysis = FirmwareAnalysis.objects.get(id=analysis_id)
    analysis.failed = False
    analysis.finished = False
    analysis.status = dict(analysis.status or {})
    analysis.status["work"] = True
    analysis.status["percentage"] = 0
    analysis.status["last_phase"] = "Queued"
    analysis.save(update_fields=["failed", "finished", "status"])
    _log_import_progress(analysis, "Import queued", 0, "Archive import queued", task=self)

    message = f"Importing {zip_path}"
    print(f"[import-task] {message}")
    logger.info(message)
    _log_import_progress(analysis, "Import starting", 1, message, task=self)

    try:
        import_results(
            str(zip_path),
            analysis_id,
            status_callback=lambda phase, percentage, message: _log_import_progress(
                analysis,
                phase,
                percentage,
                message,
                task=self,
            ),
            extract_root=extract_root,
        )
    except Exception as exc:
        analysis.failed = True
        analysis.finished = True
        analysis.end_date = timezone.now()
        analysis.duration = ""
        start_time = getattr(analysis, "start_date", None)
        if start_time is not None and not hasattr(start_time, "__call__"):
            try:
                analysis.duration = str(analysis.end_date - start_time)
            except TypeError:
                analysis.duration = ""
        analysis.status = dict(analysis.status or {})
        analysis.status["error"] = str(exc)
        analysis.status["last_error"] = str(exc)
        analysis.status["work"] = False
        analysis.status["percentage"] = 100
        _log_import_progress(analysis, "Import failed", 100, f"Archive import failed: {exc}", task=self)
        analysis.save(update_fields=["failed", "finished", "end_date", "duration", "status"])
        if getattr(self, "request", None) is not None and getattr(self.request, "id", None):
            self.update_state(state="FAILURE", meta={"analysis_id": str(analysis_id), "error": str(exc)})
        logger.exception("Import failed for analysis %s from %s", analysis_id, zip_path)
        raise

    analysis.failed = False
    analysis.finished = True
    analysis.end_date = timezone.now()
    analysis.duration = ""
    start_time = getattr(analysis, "start_date", None)
    if start_time is not None and not hasattr(start_time, "__call__"):
        try:
            analysis.duration = str(analysis.end_date - start_time)
        except TypeError:
            analysis.duration = ""
    analysis.status = dict(analysis.status or {})
    analysis.status["work"] = False
    analysis.status["percentage"] = 100
    analysis.status["last_error"] = ""
    _log_import_progress(analysis, "Import completed", 100, "Archive extraction complete", task=self)
    analysis.save(update_fields=["failed", "finished", "end_date", "duration", "status"])
    if getattr(self, "request", None) is not None and getattr(self.request, "id", None):
        self.update_state(state="SUCCESS", meta={"analysis_id": str(analysis_id), "percentage": 100})

    return analysis_id


@shared_task
def export_analysis(analysis_id, export_options):
    """
    Create an EMBArk export archive for an analysis.

    :param analysis_id: ID of the FirmwareAnalysis
    :param export_options: Selected export components
    :return: Path to the generated ZIP archive
    """
    analysis = FirmwareAnalysis.objects.get(id=analysis_id)

    export = AnalysisExport.objects.create(
        analysis=analysis,
        export_options=export_options,
        file_path="",
    )

    try:
        zip_path = export_results(
            analysis_id,
            export_options,
            export.id,
        )

        export.file_path = str(zip_path)
        export.save(update_fields=["file_path"])

        return str(zip_path)

    except Exception:
        # Don't leave a database entry for an export that failed.
        export.delete()
        raise