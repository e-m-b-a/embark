import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from django.contrib.auth import authenticate, login

from embark.users.models import User

logger = logging.getLogger('web')


@csrf_exempt
@require_http_methods(["POST"])
def signin(request):
    try:
        try:
            username = request.POST['email']
            password = request.POST['password']
        except KeyError:
            logger.exception('Missing keys from data- Username and password')
            return HttpResponse("User data is invalid")

        logger.debug(f'Found user name and password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            logger.debug(f'User authenticated')
            login(request, user)
            logger.debug(f'User logged in')
            return HttpResponse("Logged in")
        else:
            logger.debug(f'User could not be authenticated')
            return HttpResponse("User data is invalid")
    except Exception as error:
        return HttpResponse("Something went wrong when logging the user in")


@csrf_exempt
@require_http_methods(["POST"])
def signup(request):
    try:
        try:
            username = request.POST['email']
            password = request.POST['password']
            confirm_password = request.POST['confirm_password']
        except KeyError:
            logger.exception('Missing keys from data- Username, password and confirm_password')
            return HttpResponse("User data is invalid")
        if password == confirm_password:
            logger.debug(f'Passwords match. Creating user')
            user = User.objects.create(username=username, email=username)
            user.set_password(password)
            user.save()
            logger.debug(f'User created')
        else:
            logger.debug(f'Passwords do not match')
            return HttpResponse("Passwords do not match")

        user = authenticate(username=username, password=password)
        logger.debug(f'User authenticated')
        if user is not None:
            login(request, user)
            logger.debug(f'User logged in')
            return HttpResponse("Signup complete. User Logged in")
        else:
            return HttpResponse("Invalid signup data")
    except Exception as error:
        return HttpResponse("Something went wrong when signing up the user")


