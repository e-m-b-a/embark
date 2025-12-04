__copyright__ = 'Copyright 2025 The AMOS Projects'
__author__ = 'ashiven, ClProsser, SirGankalot'
__license__ = 'MIT'

from django.urls import path

from workers import views

urlpatterns = [
    path('worker/', views.worker_main, name='embark-worker-main'),
    path("worker/delete_config/", views.delete_config, name="embark-delete-configuration"),
    path("worker/create_config/", views.create_config, name="embark-create-configuration"),
    path('worker/scan/<int:configuration_id>/', views.config_worker_scan, name='embark-worker-scan'),
    path('worker/configure/<int:configuration_id>/', views.configure_worker, name='embark-worker-configure'),

    path('worker/soft_reset/<int:worker_id>/', views.worker_soft_reset, name='embark-worker-soft-reset'),
    path('worker/soft_reset/configuration/<int:configuration_id>/', views.configuration_soft_reset, name='embark-configuration-soft-reset'),
    path('worker/hard_reset/<int:worker_id>/', views.worker_hard_reset, name='embark-worker-hard-reset'),
    path('worker/hard_reset/configuration/<int:configuration_id>/', views.configuration_hard_reset, name='embark-configuration-hard-reset'),

    path('worker/update/<int:worker_id>/', views.update_worker_dependency, name='embark-worker-update'),
    path('worker/update/configuration/<int:configuration_id>/', views.update_configuration_dependency, name='embark-configuration-update'),

    path('worker/updates/', views.check_updates, name='embark-worker-check-updates'),

    path('worker/configuration/<int:configuration_id>/ssh', views.download_ssh_private_key, name='embark-configuration-sshkey-download'),
    path('worker/configuration/<int:configuration_id>/logs', views.show_configuration_logs, name='embark-configuration-logs'),

    path('worker/orchestrator/state/', views.orchestrator_state, name='embark-orchestrator-state'),
    path('worker/orchestrator/reset/', views.orchestrator_reset, name='embark-orchestrator-reset'),

    path('worker/queue/state/<int:worker_id>/', views.update_queue_state, name='embark-worker-update-queue'),
    path('worker/queue/reset/<int:worker_id>/', views.update_queue_reset, name='embark-worker-update-queue-reset'),

    path('worker/dependencies/state/', views.dependency_state, name='embark-worker-dependency-state'),
    path('worker/dependencies/reset/', views.dependency_state_reset, name='embark-worker-dependency-reset'),

    path('worker/log/<int:worker_id>/', views.show_worker_log, name='embark-worker-show-log'),
]
