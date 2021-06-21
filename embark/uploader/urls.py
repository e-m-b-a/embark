from django.conf import settings
from django.urls import path

from uploader import views


# view routing
urlpatterns = [
    path(settings.LOGIN_URL, views.login, name='embark-login'),
    path('home/', views.home, name='embark-home'),
    path('home/about/', views.about, name='embark-about'),
    path('home/upload/', views.upload_file, name='embark-upload'),
    path('home/delete/', views.delete_file, name='embark-delete'),
    path('home/upload/save_file', views.save_file, name='embark-FileSave'),
    path('home/serviceDashboard/', views.service_dashboard, name='embark-ServiceDashboard'),
    path('home/mainDashboard/', views.main_dashboard, name='embark-MainDashboard'),
    path('home/reportDashboard/', views.report_dashboard, name='embark-ReportDashboard'),
    path('download_zipped/<int:analyze_id>/', views.download_zipped, name='embark-download')
]
