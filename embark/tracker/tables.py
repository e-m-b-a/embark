import django_tables2 as tables
from uploader.models import Device, FirmwareAnalysis

class SimpleDeviceTable(tables.Table):
    class Meta:
        model = Device