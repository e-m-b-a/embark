from django.conf import settings
from django.urls import path

from . import views


# view routing
urlpatterns = [
    path('emba_logs/<str:analyze_id>/html-report/style/<str:img_file>', views.html_report_resource, name='embark-html-report-resource'),
    path('emba_logs/<str:analyze_id>/html-report/<str:html_file>', views.html_report, name='embark-html-report'),
    path('emba_logs/<str:analyze_id>/html-report/<str:html_path>/<str:html_file>', views.html_report_path, name='embark-html-report-path'),
    
    path('get_load/', views.get_load, name='embark-get-load'),
    path('get_individual_report/<str:analyze_id>/', views.get_individual_report, name='embark-get-individual-report'),
    path('get_accumulated_reports/', views.get_accumulated_reports, name='embark-get-accumulated-reports'),

    path('emba_logs/<str:analyze_id>/html-report/<path:html_path>/<str:download_file>/', views.html_report_download, name='embark-html-report-download'),
    path('download_zipped/<str:analyze_id>/', views.download_zipped, name='embark-download'),
]