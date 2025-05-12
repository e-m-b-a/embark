__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021 The AMOS Projects, Copyright 2023 Christian Bieg'
__author__ = 'm-1-k-3, diegiesskanne, Benedikt Kuehne, Garima Chauhan, Christian Bieg'
__license__ = 'MIT'

from django.urls import path
from channels.routing import URLRouter

from embark.consumers import ProgressConsumer
from embark.logviewer import AnalysisLogConsumer, UpdateLogConsumer

# url patterns for websocket communication -> equivalent to urls.py
ws_urlpatterns = URLRouter([
    path('ws/progress', ProgressConsumer.as_asgi(), name="websocket-progress"),
    path('ws/logs/<uuid:analysis_id>', AnalysisLogConsumer.as_asgi(), name="websocket-analysis-logviewer"),
    path('ws/logs/update', UpdateLogConsumer.as_asgi(), name="websocket-update-logviewer")
])
