from django.conf import settings
from django.urls import path

from uploader import views


# view routing
urlpatterns = [
    path(settings.LOGIN_URL, views.login, name='embark-login'),
    path(settings.LOGOUT_REDIRECT_URL, views.logout_view, name='embark-logout'),
    path('home/', views.home, name='embark-home'),
    path('home/upload/<int:refreshed>/', views.start_analysis, name='embark-start-analysis'),
    path('home/delete/', views.delete_file, name='embark-delete'),
    path('home/upload/<int:refreshed>/save_file', views.save_file, name='embark-FileSave'),
    path('logs/', views.get_logs, name='logs'),
    path('home/serviceDashboard/', views.service_dashboard, name='embark-ServiceDashboard'),
    path('home/mainDashboard/', views.main_dashboard, name='embark-MainDashboard'),
    path('home/reportDashboard/', views.report_dashboard, name='embark-ReportDashboard'),
    path('home/individualReportDashboard/<int:analyze_id>', views.individual_report_dashboard, name='embark-IndividualReportDashboard'),
    path('download_zipped/<int:analyze_id>/', views.download_zipped, name='embark-download'),

    path('get_load/', views.get_load, name='embark-get-load'),
    path('get_individual_report/<int:analyze_id>/', views.get_individual_report, name='embark-get-individual-report'),
    path('get_accumulated_reports/', views.get_accumulated_reports, name='embark-get-accumulated-reports'),
    path('check_login/', views.check_login, name='embark-check-login')
]
