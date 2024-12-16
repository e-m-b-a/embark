__copyright__ = 'Copyright 2022-2024 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

from django.urls import path

from tracker import views


# view routing
urlpatterns = [
    path('tracker/', views.tracker, name='embark-tracker'),
    # path('tracker/<time_delta:time>/', views.tracker, name='embark-tracker-time'),
    path('tracker/device/<int:device_id>/', views.get_report_for_device, name='embark-tracker-device'),
    path('tracker/sbom/<uuid:sbom_id>', views.get_sbom, name='embark-tracker-sbom'),
    path('tracker/device/<int:device_id>/toggle', views.toggle_device_visible, name='embark-tracker-device-visible'),
    # path('tracker/vendor/<str:vendor_name>/', views.get_report_for_vendor, name='embark-tracker-vendor'),
    path('tracker/associate/<uuid:analysis_id>', views.set_associate_device_to, name='embark-tracker-ass')
]
