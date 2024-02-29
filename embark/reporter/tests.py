__copyright__ = 'Copyright 2022-2024 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

from django.test import TestCase


class ReporterTestModel(TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        # TODO create EMBA-result with FWA and Result object

    def test_download(self):
        # TODO
        pass
