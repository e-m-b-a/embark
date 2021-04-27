from django.urls import path
from . import views

# view routing
urlpatterns = [
    path('', views.home, name='embark-home'),
    path('about/', views.about, name='embark-about'),
    path('upload/', views.upload_file, name='embark-about')
]
