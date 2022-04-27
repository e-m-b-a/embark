from django.urls import path

from uploader import views

# view routing
urlpatterns = [

    path('uploader/', views.uploader_home, name='embark-uploader-home'),
    path('uploader/save/', views.save_file, name='embark-uploader-save'),
    path('uploader/delete/', views.delete_fw_file, name='embark-uploader-delete'),
    path('uploader/start/', views.start_analysis, name='embark-uploader-start-analysis'),
    path('uploader/stop/', views.stop_analysis, name='embark-uploader-stop-analysis')
]
