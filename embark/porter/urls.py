__copyright__ = 'Copyright 2022-2026 Siemens Energy AG'
__author__ = 'Benedikt Kuehne, Eren Erguer'
__license__ = 'MIT'

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
    path('export/download/<uuid:export_id>/',views.download_export,name='embark-export-download'),
    path('export/delete/<uuid:export_id>/',views.delete_export,name='embark-export-delete'),

    path('retry-import/', views.retry_import, name='embark-retry-import'),

    #path('export/zip/<uuid:analysis_id>/', views.make_zip, name='embark-make-zip'), #FIXME: Old function, "make_zip()" replaced by "export_analysis()"

]
