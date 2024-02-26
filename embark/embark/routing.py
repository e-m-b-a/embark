__copyright__ = 'Copyright 2021-2024 Siemens Energy AG, Copyright 2021 The AMOS Projects, Copyright 2023 Christian Bieg'
__author__ = 'm-1-k-3, diegiesskanne, Benedikt Kuehne, Garima Chauhan, Christian Bieg'

from django.urls import path
# from django.urls import re_path
# from django.conf.urls import url
from embark.consumers import ProgressConsumer
from embark.logviewer import LogConsumer

# url patterns for websocket communication -> equivalent to urls.py
ws_urlpatterns = [
    path('ws/progress/', ProgressConsumer.as_asgi()),
    path('ws/logs/<uuid:analysis_id>', LogConsumer.as_asgi())
]
