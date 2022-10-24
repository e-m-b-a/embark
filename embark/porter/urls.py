from django.urls import path

from porter import views

# view routing
urlpatterns = [

    path('import/', views.import_menu, name='embark-import-menu'),
    path('import/save/', views.import_save, name='embark-import-save'),
    path('import/read/', views.import_read, name='embark-import-read'),

    path('export/', views.export_analysis, name='embark-export-menu')
]
