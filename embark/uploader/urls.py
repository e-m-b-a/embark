from django.urls import path

from uploader import views

# view routing
urlpatterns = [
    
    path('uploader/', views.uploader_home, name='embark-uploader-home'),
    path('uploader/start/', views.start_analysis, name='embark-uploader-start-analysis'),
]
