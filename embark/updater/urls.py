from django.urls import path

from updater import views

# view routing
urlpatterns = [

    path('updater/', views.updater_home, name='embark-updater-home'),
    path('updater/update-emba', views.update_emba, name='embark-updater-emba'),
    path('updater/update-cves', views.update_cves, name='embark-updater-cves')
]
