from django.urls import path
from . import views

# view routing
urlpatterns = [
    path('signin', views.signin, name='embark-signin'),
    path('signup/', views.signup, name='embark-signup'),
]