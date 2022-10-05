from django.urls import path

from dashboard import views


# view routing
urlpatterns = [
    path('dashboard/main/', views.main_dashboard, name='embark-MainDashboard'),
      # TODO add un-auth view for main dashboard
    path('dashboard/service/', views.service_dashboard, name='embark-dashboard-service'),
    path('dashboard/report/', views.report_dashboard, name='embark-ReportDashboard'),
    path('dashboard/individualReport/<uuid:analysis_id>', views.individual_report_dashboard, name='embark-IndividualReportDashboard'),
    path('dashboard/stop/', views.stop_analysis, name='embark-stop-analysis')
]
