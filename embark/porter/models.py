import shutil
import logging
import uuid

from django.conf import settings
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils.datetime_safe import datetime
from django.db import models

from users.models import User as Userclass

logger = logging.getLogger(__name__)


class LogZipFile(models.Model):
    """
    class LogZipFile
    Model to store zipped log directory for import
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=True)

    upload_date = models.DateTimeField(default=datetime.now, blank=True)
    user = models.ForeignKey(Userclass, on_delete=models.SET_NULL, related_name='Import_zip_Upload_User', null=True, blank=True)

    def get_storage_path(self, filename):
        # file will be uploaded to MEDIA_ROOT/log_zip/<id>
        return f"log_zip/{filename}"

    file = models.FileField(upload_to=get_storage_path)

    def get_abs_path(self):
        return self.file.name

    def get_abs_folder_path(self):
        return f"{settings.MEDIA_ROOT}/log_zip"

    def __str__(self):
        return f"{self.file.name.replace('/', ' - ')}"


@receiver(pre_delete, sender=LogZipFile)
def delete_zip_pre_delete_post(sender, instance, **kwargs):
    """
    callback function
    delete the zip file and folder structure in storage on recieve
    """
    if sender.file:
        shutil.rmtree(instance.get_abs_path(), ignore_errors=False, onerror=logger.error("Error when trying to delete %s", instance.get_abs_folder_path()))
    else:
        logger.error("No related file for delete request: %s", str(sender))
