from django.conf import settings
from django.urls import path

from . import views


# view routing
urlpatterns = [
    path('dashboard/main/', views.main_dashboard, name='embark-MainDashboard'),
    path('dashboard/service/', views.service_dashboard, name='embark-ServiceDashboard'),
    path('dashboard/report/', views.report_dashboard, name='embark-ReportDashboard'),
    path('dashboard/individualReport/<str:analysis_id>', views.individual_report_dashboard, name='embark-IndividualReportDashboard'),
]
