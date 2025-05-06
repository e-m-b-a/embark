# __copyright__ = 'Copyright 2022-2025 Siemens Energy AG'
# __author__ = 'Benedikt Kuehne'
# __license__ = 'MIT'
#
# import json
# import logging
# import os
# import shutil
#
# from django.conf import settings
# from django.forms import model_to_dict
# from django.test import TestCase
# from django.db import transaction
#
# from uploader.models import FirmwareAnalysis
# from porter.models import LogZipFile
# from porter.importer import result_read_in
# from users.models import User
#
# logger = logging.getLogger(__name__)
#
#
# class TestImport(TestCase):
#
#     @classmethod
#     def setUpTestData(cls) -> None:
#         cls.test_log_zip_file = os.path.join(settings.BASE_DIR.parent, "test/porter/test-log.zip")
#         with open(os.path.join(settings.BASE_DIR.parent, "test/porter/f50_test.json"), 'r', encoding='utf-8') as json_file:
#             cls.test_result_dict = json.load(json_file)
#
#     @transaction.atomic
#     def test_importer(self):
#         analysis = FirmwareAnalysis.objects.create(
#             failed=False,
#             finished=False,
#             firmware_name="TestFirmwarePorterModule",
#             user=User.objects.create(
#                 username='test-porter'
#             )
#         )
#         analysis.path_to_logs = f"{settings.EMBA_LOG_ROOT}/{analysis.id}/emba_logs"
#         # make dirs
#         os.makedirs(f"{settings.EMBA_LOG_ROOT}", exist_ok=True)
#         os.mkdir(f"{settings.EMBA_LOG_ROOT}/{analysis.id}")
#         os.mkdir(f"{settings.EMBA_LOG_ROOT}/{analysis.id}/emba_logs")
#         os.mkdir(f"{settings.EMBA_LOG_ROOT}/{analysis.id}/emba_logs/csv_logs")
#         # copy test csvs
#         shutil.copy2(os.path.join(settings.BASE_DIR.parent, "test/porter/f50_test.csv"), f"{settings.EMBA_LOG_ROOT}/{analysis.id}/emba_logs/csv_logs/f50_base_aggregator.csv")
#         shutil.copy2(os.path.join(settings.BASE_DIR.parent, "test/porter/f20_test.csv"), f"{settings.EMBA_LOG_ROOT}/{analysis.id}/emba_logs/csv_logs/f20_vul_aggregator.csv")
#         analysis.save()
#         result_obj = result_read_in(analysis_id=analysis.id)
#         self.assertTrue(result_obj)
#         result_dict = dict(model_to_dict(result_obj))
#         # check
#         self.assertTrue(int(result_dict["files"]) == int(self.test_result_dict["files"]), msg="File count of result is:" + str(result_dict["files"]) + " vs " + str(self.test_result_dict["files"]))
#
#     @transaction.atomic
#     def test_zip_import(self):
#         # first upload
#         try:
#             with open(file=self.test_log_zip_file, mode='rb') as data_file:
#                 response = self.client.post(path='/import/save', data=data_file, content_type='application/zip', follow=True)
#                 self.assertRedirects(response, '/import/')
#             # then read
#             zip_log_file = LogZipFile.objects.all().first()
#             response = self.client.post(path='/import/read', data={'zip_log_file': zip_log_file})
#             messages = list(response.context['messages'])
#             self.assertRedirects(response, '/import/')
#             self.assertEqual(len(messages), 1)
#             self.assertNotEqual(str(messages[0]), 'import failed')
#             self.assertNotEqual(str(messages[0]), 'form invalid')
#         except FileNotFoundError as exce:
#             print(f"Test file is not in folder, skipping...{exce}")
