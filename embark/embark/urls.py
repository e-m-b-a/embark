"""djangoProject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'm-1-k-3, RaviChandra, Garima Chauhan, Maximilian Wagner, diegiesskanne'
__license__ = 'MIT'

from django.contrib import admin
from django.urls import path, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('updater.urls')),
    path('', include('uploader.urls')),
    path('', include('users.urls')),
    path('', include('dashboard.urls')),
    path('', include('reporter.urls')),
    path('', include('tracker.urls')),
    path('', include('porter.urls')),
    path('', include('workers.urls')),
] + staticfiles_urlpatterns()
