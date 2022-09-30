import django_tables2 as tables
from uploader.models import Device


class SimpleDeviceTable(tables.Table):

    class Meta:
        model = Device
