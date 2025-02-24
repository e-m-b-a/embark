__copyright__ = 'Copyright 2022-2025 Siemens Energy AG, Copyright 2023 Christian Bieg'
__author__ = 'Benedikt Kuehne, Christian Bieg'
__license__ = 'MIT'

from django.urls import path

from dashboard import views


# view routing
urlpatterns = [
    path('', views.main_dashboard, name='embark-MainDashboard'),
    path('dashboard/', views.main_dashboard, name='embark-MainDashboard'),
    path('dashboard/main/', views.main_dashboard, name='embark-MainDashboard'),
    path('dashboard/service/', views.service_dashboard, name='embark-dashboard-service'),
    path('dashboard/report/', views.report_dashboard, name='embark-ReportDashboard'),
    path('dashboard/report/deleteAnalysis/<uuid:analysis_id>', views.delete_analysis, name='embark-dashboard-delete-analysis'),
    path('dashboard/report/archive/<uuid:analysis_id>', views.archive_analysis, name='embark-dashboard-archive'),
    path('dashboard/report/hide/<uuid:analysis_id>', views.hide_analysis, name='embark-dashboard-hide'),
    path('dashboard/individualReport/<uuid:analysis_id>', views.individual_report_dashboard, name='embark-IndividualReportDashboard'),
    path('dashboard/stop/', views.stop_analysis, name='embark-stop-analysis'),
    path('dashboard/log/<uuid:analysis_id>', views.show_log, name='embark-show-log'),
    path('dashboard/logviewer/<uuid:analysis_id>', views.show_logviewer, name='embark-show-logviewer'),
    path('dashboard/report/createlabel/', views.create_label, name='embark-dashboard-create-label'),
    path('dashboard/report/addlabel/<uuid:analysis_id>', views.add_label, name='embark-dashboard-add-label'),
    path('dashboard/report/rmlabel/<uuid:analysis_id><str:label_name>', views.rm_label, name='embark-dashboard-remove-label'),
]
