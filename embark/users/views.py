from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from django.contrib.auth import authenticate, login

from embark.users.models import User


@csrf_exempt
@require_http_methods(["POST"])
def signin(request):
    try:
        username = request.POST['email']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return HttpResponse("Logged in")
        else:
            return HttpResponse("User data is invalid")
    except Exception as error:
        return HttpResponse("Something went wrong when logging the user in")


@csrf_exempt
@require_http_methods(["POST"])
def signup(request):
    try:
        username = request.POST['email']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        if password == confirm_password:
            user = User.objects.create(username=username, email=username)
            user.set_password(password)
            user.save()
        else:
            return HttpResponse("Passwords do not match")

        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return HttpResponse("Signup complete. User Logged in")
        else:
            return HttpResponse("Invalid signup data")
    except Exception as error:
        return HttpResponse("Something went wrong when signing up the user")


