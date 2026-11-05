__copyright__ = 'Copyright 2022-2026 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

import os
import logging
import uuid

from django.conf import settings
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.db import models

from users.models import User as Userclass

logger = logging.getLogger(__name__)


class LogZipFile(models.Model):
    """
    class LogZipFile
    Model to store zipped log directory for import
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=True)

    upload_date = models.DateTimeField(default=timezone.now, blank=True)
    user = models.ForeignKey(Userclass, on_delete=models.SET_NULL, related_name='Import_zip_Upload_User', null=True, blank=True)

    def get_storage_path(self, filename):
        # file will be uploaded to MEDIA_ROOT/log_zip/<id>
        return f"log_zip/{filename}"

    file = models.FileField(upload_to=get_storage_path)

    def get_abs_path(self):
        return f"{settings.MEDIA_ROOT}/log_zip/{os.path.basename(self.file.name)}"

    def get_abs_folder_path(self):
        return f"{settings.MEDIA_ROOT}/log_zip"

    def __str__(self):
        return f"{self.file.name.replace('/', ' - ')}"

class AnalysisExport(models.Model):
    """
    Stores metadata for an exported EMBArk analysis.

    Each export has its own UUID so multiple exports of the
    same analysis can coexist with different export options.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    analysis = models.ForeignKey(
        "uploader.FirmwareAnalysis", # Importing uploader.FirmwareAnalysis not possible due to circular imports (Uploader uses LogZipFile)
        on_delete=models.CASCADE,
        related_name="exports",
    )

    created_at = models.DateTimeField(
        default=timezone.now,
    )

    export_options = models.JSONField(
        default=list,
    )

    file_path = models.TextField()

    def __str__(self):
        return f"Export {self.id} - Analysis {self.analysis_id}"


@receiver(pre_delete, sender=LogZipFile)
def delete_zip_pre_delete_post(sender, instance, **kwargs):
    """
    callback function
    delete the zip file and folder structure in storage on recieve
    """
    try:
        path = instance.get_abs_path()
        if os.path.exists(path):
            os.remove(path)
        else:
            logger.debug("Zip file path does not exist: %s", path)
    except Exception as exc:  # pragma: no cover - defensive cleanup
        logger.exception("Failed to remove zip file: %s", exc)
