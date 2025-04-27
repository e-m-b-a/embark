__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021 The AMOS Projects, Copyright 2021 Siemens AG'
__author__ = 'Benedikt Kuehne, Maximilian Wagner, p4cx, Ashutosh Singh, VAISHNAVI UMESH, diegiesskanne, uk61elac, RaviChandra, Vaish1795, Garima Chauhan, m-1-k-3'
__license__ = 'MIT'

from django.urls import path
from .views import UploaderView
from uploader import views

# view routing
urlpatterns = [

    path('uploader/', views.uploader_home, name='embark-uploader-home'),

    path('api/uploader/', UploaderView.as_view()),

    path('uploader/manage/', views.manage_file, name='embark-uploader-manage-file'),
    path('uploader/save/', views.save_file, name='embark-uploader-save'),
    path('uploader/delete/', views.delete_fw_file, name='embark-uploader-delete'),

    path('uploader/start/', views.start_analysis, name='embark-uploader-start-analysis'),

    path('uploader/device/', views.device_setup, name='embark-uploader-device'),
    path('uploader/vendor/', views.vendor, name='embark-uploader-vendor'),
    path('uploader/label/', views.label, name='embark-uploader-label'),

    path('uploader-minimal/', views.uploader_home_minimal, name='embark-uploader-home-minimal'),
]
