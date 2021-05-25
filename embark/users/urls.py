from django.urls import path, include
from . import views


urlpatterns = [
    path('', include('uploader.urls')),
    path('signin', views.signin, name='embark-signin'),
    path('signup', views.signup, name='embark-signup'),
]
