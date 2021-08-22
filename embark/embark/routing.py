from django.urls import path
# from django.urls import re_path
# from django.conf.urls import url
from . import consumers

# url patterns for websocket communication -> equivalent to urls.py
# TODO: adjust url after progress example is removed
ws_urlpatterns = [
    path('ws/progress/', consumers.WSConsumer.as_asgi()),
]
