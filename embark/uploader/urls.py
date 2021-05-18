from django.urls import path
from . import views

# view routing
urlpatterns = [
    path('', views.login, name='embark-login'),
    path('home/', views.home, name='embark-home'),
    path('about/', views.about, name='embark-about'),
    path('upload/', views.upload_file, name='embark-File'),
    path('upload/save_file', views.save_file, name='embark-FileSave'),
    path('serviceDashboard/', views.serviceDashboard, name='embark-ServiceDashboard'),
]
