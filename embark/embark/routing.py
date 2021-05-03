from django.urls import path
from . import consumers
from django.urls import re_path
from django.conf.urls import url

ws_urlpatterns = [
    path('ws/progress', consumers.WSConsumer.as_asgi()),
]
