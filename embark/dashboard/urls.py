from django.urls import path

from . import views


# view routing
urlpatterns = [
    path('dashboard/main/', views.main_dashboard, name='embark-MainDashboard'),
    path('dashboard/service/', views.service_dashboard, name='embark-ServiceDashboard'),
    path('dashboard/report/', views.report_dashboard, name='embark-ReportDashboard'),
    path('dashboard/individualReport/<uuid:analysis_id>', views.individual_report_dashboard, name='embark-IndividualReportDashboard'),
    path('dashboard/stop/', views.stop_analysis, name='embark-stop-analysis'),
    path('get_report_for_device/<str:device_name>/', views.get_report_for_device, name='embark-dashboard-get-for-device'),
]
