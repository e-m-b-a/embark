from django.urls import path

from tracker import views


# view routing
urlpatterns = [
    path('tracker/', views.tracker, name='embark-tracker'),
    # path('tracker/<time_delta:time>/', views.tracker, name='embark-tracker-time'),
    path('tracker/device/<int:device_id>/', views.get_report_for_device, name='embark-tracker-device'),
    # path('tracker/vendor/<str:vendor_name>/', views.get_report_for_vendor, name='embark-tracker-vendor'),
]
