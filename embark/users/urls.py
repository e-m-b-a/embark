from django.conf import settings
from django.urls import path

from users import views


urlpatterns = [
    path(settings.LOGIN_URL, views.login, name='embark-login'),
    path('signup/', views.signup, name='embark-signup'),
    path('logout/', views.logout, name='embark-logout'),
    path('password_change/', views.password_change, name='embark-password'),
    path('acc_delete/', views.acc_delete, name='embark-acc-delete')
]
