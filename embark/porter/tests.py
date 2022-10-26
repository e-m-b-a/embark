import json
import logging
import os
from django.conf import settings
from django.forms import model_to_dict
from django.test import TestCase

from uploader.models import FirmwareAnalysis
from porter.importer import import_log_dir, result_read_in

logger = logging.getLogger(__name__)


class TestImport(TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.test_log_zip_file = os.path.join(settings.BASE_DIR.parent, "test/porter/test-log.zip")

        with open(os.path.join(settings.BASE_DIR.parent, "test/porter/test-log.zip"), 'r', encoding='utf-8') as json_file:
            cls.test_result_dict = json.load(json_file)
            # TODO get json for comparison

    def test_importer(self):
        analysis = FirmwareAnalysis.objects.create()
        analysis.failed = False
        analysis.finished = False
        analysis.device = None
        analysis.firmware_name = "TestFirmwareNoname"
        analysis.user = None
        # TODO

        analysis.save()
        self.assertTrue(import_log_dir(log_path=self.test_log_zip_file, analysis_id=analysis.id))
        result_obj = result_read_in(analysis_id=analysis.id)
        result_dict = dict(model_to_dict(result_obj))
        # check
        self.assertDictEqual(d1=self.test_result_dict, d2=result_dict)
