from django.urls import path

from porter import views

# view routing
urlpatterns = [

    path('import/', views.import_menu, name='embark-import-menu'),
    path('import/save/', views.import_save, name='embark-import-save'),
    path('import/delete/', views.import_delete, name='embark-import-delete'),
    path('import/read/', views.import_read, name='embark-import-read'),

    path('export/', views.export_menu, name='embark-export-menu'),
    path('export/download/', views.export_analysis, name='embark-export-analysis'),
    path('export/zip/<uuid:analysis_id>/', views.make_zip, name='embark-make-zip')


]
