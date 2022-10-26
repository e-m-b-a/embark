from django.urls import path

from uploader import views

# view routing
urlpatterns = [

    path('uploader/', views.uploader_home, name='embark-uploader-home'),

    path('uploader/manage/', views.manage_file, name='embark-uploader-manage-file'),
    path('uploader/save/', views.save_file, name='embark-uploader-save'),
    path('uploader/delete/', views.delete_fw_file, name='embark-uploader-delete'),

    path('uploader/start/', views.start_analysis, name='embark-uploader-start-analysis'),

    path('uploader/device/', views.device_setup, name='embark-uploader-device'),
    path('uploader/vendor/', views.vendor, name='embark-uploader-vendor'),
    path('uploader/label/', views.label, name='embark-uploader-label'),

    # path('uploader/import/', views.import_analysis, name='embark-uploader-import'),
    # path('uploader/read/', views.read_analysis, name='embark-uploader-read'),
]
