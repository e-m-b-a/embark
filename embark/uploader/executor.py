import logging
import os
import shutil

from django.conf import settings
from uploader.models import FirmwareAnalysis, FirmwareFile
from uploader.archiver import Archiver
from uploader.boundedexecutor import BoundedExecutor
from uploader.settings import workers_enabled
from workers.orchestrator import WorkerOrchestrator, OrchestratorTask
from embark.logreader import LogReader


logger = logging.getLogger(__name__)


def submit_firmware(firmware_analysis: FirmwareAnalysis, firmware_file: FirmwareFile):
    """
    submit firmware + metadata for emba execution

    params firmware_analysis: firmware model with flags and metadata
    params firmware_file: firmware file model to be analyzed

    return: emba process future on success, None on failure
    """
    active_analyzer_dir = f"{settings.ACTIVE_FW}/{firmware_analysis.id}/"
    logger.info("submitting firmware %s to emba", active_analyzer_dir)

    Archiver.copy(src=firmware_file.file.path, dst=active_analyzer_dir)

    # copy success
    emba_startfile = os.listdir(active_analyzer_dir)
    logger.debug("active dir contents %s", emba_startfile)
    if len(emba_startfile) == 1:
        image_file_location = f"{active_analyzer_dir}{emba_startfile.pop()}"
    else:
        logger.error("Uploaded file: %s doesnt comply with processable files.", firmware_file)
        logger.error("Zip folder with no extra directory in between.")
        shutil.rmtree(active_analyzer_dir)
        return None

    firmware_analysis.create_log_dir()
    firmware_analysis.set_meta_info()

    if workers_enabled():
        target = f"{settings.WORKER_FIRMWARE_DIR}{emba_startfile.pop()}"
        emba_cmd = firmware_analysis.construct_emba_command(target)

        # TODO: Replace with actual Orchestrator instance
        orchestrator = WorkerOrchestrator()
        orchestrator.assign_task(OrchestratorTask(firmware_analysis, emba_cmd, image_file_location, target))

        return True
    else:
        emba_cmd = firmware_analysis.construct_emba_command(image_file_location)
        emba_fut = BoundedExecutor.submit(BoundedExecutor.run_emba_cmd, emba_cmd, firmware_analysis.id, active_analyzer_dir)
        BoundedExecutor.submit(LogReader, firmware_analysis.id)

        return bool(emba_fut)
