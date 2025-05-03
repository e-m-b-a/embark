from functools import wraps

from django.http import JsonResponse
from users.models import User


def require_api_key(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        api_key = request.headers.get("Authorization") or request.GET.get("api_key")
        if not api_key:
            return JsonResponse({"error": "Missing API key"}, status=401)

        try:
            user = User.objects.get(api_key=api_key)
            request.api_user = user
        except User.DoesNotExist:
            return JsonResponse({"error": "Invalid API key"}, status=401)

        return view_func(request, *args, **kwargs)

    return _wrapped_view
