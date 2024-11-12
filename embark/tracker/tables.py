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

    def render_properties(self, value, record):
        return format_html(
            '<button class="btn btn-primary" type="button" data-bs-toggle="collapse" data-bs-target="#collapsePoperties{}" aria-expanded="false" aria-controls="collapsePoperties{}" title="Show Properties {}">'
            "show"
            "</button>"
            '<div class="collapse" id="collapsePoperties{}">'
            '{}'
            '</div', record.id, record.id, record.id, record.id, value
        )

    class Meta:
        model = SoftwareInfo
        orderable = True
        fields = ("id", "name", "type", "version", "hashes", "cpe", "purl", "properties", )


class SimpleResultTable(tables.Table):

    class Meta:
        model = Result
        orderable = True
        fields = ("firmware_analysis", "date", "vulnerability", "sbom_id", )

    def render_sbom_id(self, value):
        return format_html(f"<a href=\"{reverse(viewname='embark-tracker-sbom', args=[value])}\">{value}</a>")
