from django.conf import settings
from django.urls import path

from uploader import views


# view routing
urlpatterns = [
    path(settings.LOGIN_URL, views.login, name='embark-login'),
    path('home/', views.home, name='embark-home'),
    path('home/about/', views.about, name='embark-about'),
    path('home/upload/', views.upload_file, name='embark-File'),
    path('home/upload/save_file', views.save_file, name='embark-FileSave'),
    path('home/serviceDashboard/', views.service_dashboard, name='embark-ServiceDashboard'),
    path('start/', views.start, name='embark-start')
]
