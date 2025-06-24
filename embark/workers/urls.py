__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021 The AMOS Projects, Copyright 2021 Siemens AG'
__author__ = 'Garima Chauhan, YulianaPoliakova, Benedikt Kuehne, VAISHNAVI UMESH, p4cx, m-1-k-3'
__license__ = 'MIT'

from django.urls import path

from workers import views

urlpatterns = [
    path('worker/', views.worker_main, name='embark-worker-main'),
    path("worker/delete_config/", views.delete_config, name="embark-delete-configuration"),
    path("worker/create_config/", views.create_config, name="embark-create-configuration"),
    path('worker/scan/<int:configuration_id>/', views.config_worker_scan, name='embark-worker-scan'),
    path('worker/configure/<int:configuration_id>/', views.configure_worker, name='embark-worker-configure'),
    path('worker/connect/<int:configuration_id>/<int:worker_id>/', views.connect_worker, name='embark-worker-connect'),
    path('worker/registered/<int:configuration_id>/', views.registered_workers, name='embark-worker-registered'),     # TODO: convert to API endpoints after development complete

    path('worker/soft_reset/<int:worker_id>/', views.worker_soft_reset, name='embark-worker-soft-reset'),
    path('worker/soft_reset/configuration/<int:configuration_id>/', views.configuration_soft_reset, name='embark-configuration-soft-reset'),
    path('worker/hard_reset/<int:worker_id>/', views.worker_hard_reset, name='embark-worker-hard-reset'),
    path('worker/hard_reset/configuration/<int:configuration_id>/', views.configuration_hard_reset, name='embark-configuration-hard-reset'),

    path('worker/update/<int:worker_id>/', views.update_worker_dependency, name='embark-worker-update'),
    path('worker/update/configuration/<int:configuration_id>/', views.update_configuration_dependency, name='embark-configuration-update'),

    path('worker/updates/', views.check_updates, name='embark-worker-check-updates')
]
