from django.urls import path
from . import views

# view routing
urlpatterns = [
    path('', views.login, name='embark-login'),
    path('home/', views.home, name='embark-home'),
    path('home/about/', views.about, name='embark-about'),
    path('home/upload/', views.upload_file, name='embark-upload'),
    path('home/upload/save_file', views.save_file, name='embark-FileSave'),
    path('home/serviceDashboard/', views.serviceDashboard, name='embark-ServiceDashboard'),
    path('home/reports/', views.reports, name='embark-Reports'),
    path('home/mainDashboard/', views.mainDashboard, name='embark-MainDashboard'),
    # debug
    path('progress/', views.progress, name='embark-progress'),
    path('start/', views.start, name='embark-start')
]
