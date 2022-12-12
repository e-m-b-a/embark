import json
import logging
import os

from django.conf import settings
from django.forms import model_to_dict
from django.test import TestCase

from uploader.models import FirmwareAnalysis
from porter.importer import result_read_in
from users.models import User

logger = logging.getLogger(__name__)


class TestImport(TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.test_log_zip_file = os.path.join(settings.BASE_DIR.parent, "test/porter/test-log.zip")

        with open(os.path.join(settings.BASE_DIR.parent, "test/porter/test.json"), 'r', encoding='utf-8') as json_file:
            cls.test_result_dict = json.load(json_file)

    def test_importer(self):
        analysis = FirmwareAnalysis.objects.create(
            failed=False,
            finished=False,
            firmware_name="TestFirmwarePorterModule",
            user=User.objects.create(
                username='test-porter'
            )
        )
        analysis.path_to_logs = f"{settings.EMBA_LOG_ROOT}/{analysis.id}/emba_logs"

        analysis.save()
        self.assertTrue(result_read_in(analysis_id=analysis.id))
        result_obj = result_read_in(analysis_id=analysis.id)
        result_dict = dict(model_to_dict(result_obj))
        # check
        self.assertDictEqual(d1=self.test_result_dict, d2=result_dict)
