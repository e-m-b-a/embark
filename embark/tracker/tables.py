from django.urls import reverse
import django_tables2 as tables
from django.utils.html import format_html
from uploader.models import Device


class SimpleDeviceTable(tables.Table):

    class Meta:
        model = Device
        attr = {

        }

    def render_id(self, value):
        return format_html("<a href=\"%s\">%s</a>" % (reverse(viewname='embark-tracker-device', args=[value]), value))
