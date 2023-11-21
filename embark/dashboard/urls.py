from django.urls import path

from dashboard import views


# view routing
urlpatterns = [
    path('dashboard/main/', views.main_dashboard, name='embark-MainDashboard'),
    path('dashboard/service/', views.service_dashboard, name='embark-dashboard-service'),
    path('dashboard/report/', views.report_dashboard, name='embark-ReportDashboard'),
    path('dashboard/report/deleteAnalysis/<uuid:analysis_id>', views.delete_analysis, name='embark-dashboard-delete-analysis'),
    path('dashboard/report/archive/<uuid:analysis_id>', views.archive_analysis, name='embark-dashboard-archive'),
    path('dashboard/individualReport/<uuid:analysis_id>', views.individual_report_dashboard, name='embark-IndividualReportDashboard'),
    path('dashboard/stop/', views.stop_analysis, name='embark-stop-analysis'),
    path('dashboard/log/<uuid:analysis_id>', views.show_log, name='embark-show-log'),
    path('dashboard/logviewer/<uuid:analysis_id>', views.show_logviewer, name='embark-show-logviewer')
]
