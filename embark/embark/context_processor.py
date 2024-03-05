from django.conf import settings

def embark_version(request):
    return {'EMBARK_VERSION': settings.VERSION[0], 'EMBA_VERSION': settings.VERSION[1]}
