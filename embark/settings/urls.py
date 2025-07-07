__copyright__ = 'Copyright 2025 Siemens Energy AG, Copyright 2025 The AMOS Projects'
__author__ = 'ashiven, SirGankalot'
__license__ = 'MIT'

from django.urls import path

from settings import views


urlpatterns = [
    path('settings/', views.settings_main, name='embark-settings-main'),
    path('settings/toggle-orchestrator/', views.toggle_orchestrator, name='embark-settings-toggle-orchestrator'),
]
