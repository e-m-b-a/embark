from django.conf import settings
from django.urls import path

from uploader import views


# view routing
urlpatterns = [
    
    path('uploader/', views.uploader_home, name='embark-uploader-home'),
    path('uploader/save_file/', views.save_file, name='embark-uploader-filesave'),
    path('uploader/start/', views.start_analysis, name='embark-uploader-start-analysis'),

    # TODO make new applets for the rest
    
    path('uploader/serviceDashboard/', views.service_dashboard, name='embark-ServiceDashboard'),
    path('uploader/mainDashboard/', views.main_dashboard, name='embark-MainDashboard'),
    path('uploader/reportDashboard/', views.report_dashboard, name='embark-ReportDashboard'),
    path('uploader/individualReportDashboard/<str:hash_id>', views.individual_report_dashboard, name='embark-IndividualReportDashboard'),
    path('uploader/log/<int:log_type>/<int:lines>/', views.get_log, name='log'),

    path('download_zipped/<int:analyze_id>/', views.download_zipped, name='embark-download'),

    path('emba_logs/<int:analyze_id>/html-report/style/<str:img_file>', views.html_report_resource, name='embark-html-report-resource'),
    path('emba_logs/<int:analyze_id>/html-report/<str:html_file>', views.html_report, name='embark-html-report'),
    path('emba_logs/<int:analyze_id>/html-report/<str:html_path>/<str:html_file>', views.html_report_path, name='embark-html-report-path'),
    path('emba_logs/<int:analyze_id>/html-report/<path:html_path>/<str:download_file>', views.html_report_download, name='embark-html-report-download'),

    path('get_load/', views.get_load, name='embark-get-load'),
    path('get_individual_report/<int:analyze_id>/', views.get_individual_report, name='embark-get-individual-report'),
    path('get_accumulated_reports/', views.get_accumulated_reports, name='embark-get-accumulated-reports')
]
