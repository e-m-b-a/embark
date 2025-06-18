__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2025 The AMOS Projects'
__author__ = 'ashiven, SirGankalot, ClProsser'
__license__ = 'MIT'

from functools import wraps
from django.http import JsonResponse, HttpRequest
from users.models import User


def require_api_key(view_func):
    @wraps(view_func)
    def _wrapped_view(*args, **kwargs):
        # Django REST Framework prepends the argument *self*, while Django does not
        request = args[0] if isinstance(args[0], HttpRequest) else args[1]

        api_key = request.headers.get("Authorization") or request.GET.get("api_key")
        if not api_key:
            return JsonResponse({"error": "Missing API key"}, status=401)

        try:
            user = User.objects.get(api_key=api_key)
            request.api_user = user
            request.user = user  # For compatibility with Django's request.user
        except User.DoesNotExist:
            return JsonResponse({'error': 'Invalid API key'}, status=401)

        return view_func(*args, **kwargs)

    return _wrapped_view
