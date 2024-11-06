# pylint: disable=C0413
"""
ASGI config for djangoProject project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""
__copyright__ = 'Copyright 2021-2024 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'Benedikt Kuehne, diegiesskanne, m-1-k-3'
__license__ = 'MIT'

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter
from channels.routing import URLRouter
from django.core.asgi import get_asgi_application

asgi_application = get_asgi_application()

from embark.routing import ws_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'embark.settings.deploy')


application = ProtocolTypeRouter({
    'http': asgi_application,
    'websocket': AuthMiddlewareStack(URLRouter(ws_urlpatterns))
})
