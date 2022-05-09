from django.conf import settings
from django.urls import path

from users import views


urlpatterns = [
    path(settings.LOGIN_URL, views.embark_login, name='embark-login'),
    path('user/', views.menu, name='embark-user-menu'),
    path('register/', views.register, name='embark-register'),
    path('logout/', views.embark_logout, name='embark-logout'),
    # TODO account menu path('my-account/', views., name='embark-), for admin options etc
    path('my-account/password_change/', views.password_change, name='embark-password-change'),
    path('my-account/acc_delete/', views.acc_delete, name='embark-acc-delete'),
    path('log/<int:log_type>/<int:lines>/', views.get_log, name='log'),
]
