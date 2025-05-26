__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2025 The AMOS Projects'
__author__ = 'Benedikt Kuehne, Luka Dekanozishvili'
__license__ = 'MIT'

from django.conf import settings
from django.urls import path

from reporter import views


# view routing
urlpatterns = [
    # TODO get rid of the emba log paths
    path(settings.EMBA_LOG_URL + '<uuid:analysis_id>/<str:html_file>', views.html_report, name='embark-html-report-index'),
    path(settings.EMBA_LOG_URL + '<uuid:analysis_id>/style/<str:img_file>', views.html_report_resource, name='embark-html-report-resource'),
    path(settings.EMBA_LOG_URL + '<uuid:analysis_id>/<path:html_path>/<str:file>', views.html_report_path, name='embark-html-report-path'),
    path('get_load/', views.get_load, name='embark-get-load'),
    path('get_individual_report/<uuid:analysis_id>/', views.get_individual_report, name='embark-get-individual-report'),
    path('get_accumulated_reports/', views.get_accumulated_reports, name='embark-get-accumulated-reports'),
    path('download_zipped/<uuid:analysis_id>/', views.download_zipped, name='embark-download'),
    path('status_report/<uuid:analysis_id>', views.status_report, name='embark-status-report'),
]
