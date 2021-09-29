# from django.urls import path, include
from django.urls import path
from . import views


urlpatterns = [
    path('signin', views.signin, name='embark-signin'),
    path('signup', views.signup, name='embark-signup'),
    path('signout', views.signout, name='embark-signout')
]
