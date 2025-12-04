__copyright__ = 'Copyright 2025 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

from django.urls import path

from updater import views

# view routing
urlpatterns = [
    path('updater/', views.updater_home, name='embark-updater-home'),
    path('updater/update-emba', views.update_emba, name='embark-updater-update'),
    path('updater/upgrade-emba', views.upgrade_emba, name='embark-updater-upgrade'),
    path('updater/check-emba', views.check_update, name='embark-updater-check'),
    path('updater/raw-progress', views.raw_progress, name='embark-updater-raw')
]
