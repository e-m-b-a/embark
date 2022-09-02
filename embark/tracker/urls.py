from django.urls import path

from . import views


# view routing
urlpatterns = [
    path('tracker/', views.tracker, name='embark-tracker'),
    path('tracker/device/<str:device_name>/', views.get_report_for_device, name='embark-tracker-device'),
]