__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021 The AMOS Projects, Copyright 2021 Siemens AG'
__author__ = 'Garima Chauhan, YulianaPoliakova, Benedikt Kuehne, VAISHNAVI UMESH, p4cx, m-1-k-3'
__license__ = 'MIT'

from django.urls import path

from workers import views

urlpatterns = [
    path('worker/scan/<int:configuration_id>/', views.config_worker_scan, name='embark-worker-scan'),
    path('worker/connect/<int:configuration_id>/<int:worker_id>/', views.connect_worker, name='embark-worker-connect'),
    path('worker/registered/<int:configuration_id>/', views.registered_workers, name='embark-worker-registered'),
]
