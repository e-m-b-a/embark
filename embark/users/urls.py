__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021 The AMOS Projects, Copyright 2021 Siemens AG'
__author__ = 'Garima Chauhan, YulianaPoliakova, Benedikt Kuehne, VAISHNAVI UMESH, p4cx, m-1-k-3'
__license__ = 'MIT'

from django.conf import settings
from django.urls import path

from users import views


urlpatterns = [
    path(settings.LOGIN_URL, views.embark_login, name='embark-login'),
    path('user/', views.user_main, name='embark-user-main'),
    path('user/register/', views.register, name='embark-register'),
    path('user/activate/<int:user_id>/<str:token>/', views.activate, name='embark-activate-user'),
    path('user/reset_password/', views.reset_password, name='embark-password-reset'),
    path(settings.LOGOUT_REDIRECT_URL, views.embark_logout, name='embark-logout'),
    path('user/password_change/', views.password_change, name='embark-password-change'),
    path('user/delete/', views.acc_delete, name='embark-acc-delete'),
    path('user/<int:user_id>/deactivate', views.deactivate, name='embark-deactivate-user'),
    path('user/set_timezone/', views.set_timezone, name='embark-acc-timezone'),
    path("user/generate_api_key/", views.generate_api_key, name="embark-acc-apikey"),
    path("user/api_test/", views.api_test, name="embark-api-test"),
    path('log/<int:log_type>/<int:lines>/', views.get_log, name='log'),     # TODO move to admin
]