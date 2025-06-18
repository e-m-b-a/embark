__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021 The AMOS Projects, Copyright 2021 Siemens AG'
__author__ = 'Garima Chauhan, YulianaPoliakova, Benedikt Kuehne, VAISHNAVI UMESH, p4cx, m-1-k-3'
__license__ = 'MIT'

from django.urls import path

from settings import views


urlpatterns = [
    path('settings/', views.settings_main, name='embark-settings-main'),
    path('settings/toggle-orchestrator/', views.toggle_orchestrator, name='embark-settings-toggle-orchestrator'),
]
