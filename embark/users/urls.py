# from django.urls import path, include
from django.urls import path
from . import views


urlpatterns = [
    path('signin', views.signin, name='embark-signin'),
    path('signup', views.signup, name='embark-signup'),
    path('signout', views.signout, name='embark-signout'),
    path('password_change', views.password_change, name='embark-password'),
    path('password_reset', views.password_reset, name='embark-reset'),
    path('acc_delete', views.acc_delete, name='embark-delete')
]
