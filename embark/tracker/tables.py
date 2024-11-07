__copyright__ = 'Copyright 2022-2024 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

import django_tables2 as tables

from django.utils.html import format_html
from django.urls import reverse

from dashboard.models import Result, SoftwareInfo
from uploader.models import Device


class SimpleDeviceTable(tables.Table):

    class Meta:
        model = Device
        orderable = True

    def render_id(self, value):
        return format_html(f"<a href=\"{reverse(viewname='embark-tracker-device', args=[value])}\">{value}</a>")


class SimpleSBOMTable(tables.Table):

    class Meta:
        model = SoftwareInfo
        orderable = True

    #  def render_id(self, value):
    #      return format_html(f"<a href=\"{reverse(viewname='embark-tracker-sbom', args=[value])}\">{value}</a>")


class SimpleResultTable(tables.Table):

    class Meta:
        model = Result
        orderable = True
