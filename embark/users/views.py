import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from .models import User
from django.conf import settings

logger = logging.getLogger('web')


@csrf_exempt
@require_http_methods(["GET", "POST"])
def signin(request):
    if request.method == "POST":
        logger.debug(request.POST)
        data = {k: v[0] for k, v in dict(request.POST).items()}
        logger.debug(data)
        try:
            body = {k: v[0] for k, v in dict(request.POST).items()}
            try:
                username = body['username']
                password = body['password']
            except KeyError:
                logger.exception('Missing keys from data- Username and password')
                return render(request, 'uploader/login.html',
                              {'error_message': True, 'message': 'Username or password are wrong.'})

            logger.debug('Found user name and password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                logger.debug('User authenticated')
                login(request, user)
                logger.debug('User logged in')
                return redirect('embark-home')
            # else:
            logger.debug('User could not be authenticated')
            messages.info(request, "Invalid user data")
            return render(request, 'uploader/login.html', {'error_message': True, 'message': 'Invalid user data.'})
        except Exception as error:
            logger.exception('Wide exception in Signup: %s', error)
            messages.info(request, "Invalid user data")
            return render(request, 'uploader/login.html',
                          {'error_message': True, 'message': 'Something went wrong when signing in the user.'})
    else:
        return render(request, 'login.html')


@csrf_exempt
@require_http_methods(["GET", "POST"])
def signup(request):
    if request.method == "POST":
        logger.debug(request.POST)
        data = {k: v[0] for k, v in dict(request.POST).items()}
        logger.debug(data)
        try:
            body = {k: v[0] for k, v in dict(request.POST).items()}
            try:
                username = body['username']
                password = body['password']
                confirm_password = body['confirm_password']

                if password == confirm_password:
                    logger.debug('Passwords match. Creating user')
                    user = User.objects.create(username=username)
                    user.set_password(password)
                    user.save()
                    logger.debug('User created')
                else:
                    logger.debug('Passwords do not match')
                    return render(request, 'uploader/register.html',
                                  {'error_message': True, 'message': 'Passwords do not match.'})

                return render(request, 'uploader/login.html',
                              {'success_message': True, 'message': 'Registration successful.'})

            except KeyError:
                logger.exception('Missing keys from data- Username, password, password_confirm')
                return render(request, 'uploader/register.html',
                              {'error_message': True, 'message': 'User data is invalid.'})
        except Exception as error:
            logger.exception('Wide exception in Signup: %s', error)
            return render(request, 'uploader/register.html',
                          {'error_message': True, 'message': 'Something went wrong when signing up the user.'})
    else:
        return render(request, 'register.html')


@csrf_exempt
# @cache_control(no_cache=True, must_revalidate=True, no_store=True)
def signout(request):
    # request.session.flush()
    logger.debug("Logout user %s", request.user)
    logout(request)
    return render(request, 'uploader/login.html', {'success_message': True, 'message': 'Logout successful.'})


@csrf_exempt
@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET", "POST"])
def password_change(request):
    if request.method == "POST":
        logger.debug(request.POST)
        data = {k: v[0] for k, v in dict(request.POST).items()}
        logger.debug(data)
        try:
            body = {k: v[0] for k, v in dict(request.POST).items()}
            try:
                oldPassword = body['oldPassword']
                newPassword = body['newPassword']
                confirmPassword = body['confirmPassword']

                if User.check_password(oldPassword):
                    if newPassword == confirmPassword:
                        User.set_password(newPassword)
                        logger.debug('New password set')
                    else:
                        logger.debug('Passwords do not match')
                        return render(request, 'uploader/passwordChange.html',
                                      {'error_message': True, 'message': 'Passwords do not match.'})
                    return render(request, 'uploader/base.html',
                              {'success_message': True, 'message': 'Password change successful.'})
                else:
                    logger.debug('Old password is incorrect')
                    return render(request, 'uploader/passwordChange.html',
                              {'error_message': True, 'message': 'Old password is incorrect.'})
            except KeyError:
                logger.exception('Missing keys from data-passwords')
                return render(request, 'uploader/passwordChange.html', {'error_message': True, 'message': 'Some fields are empty!'})
        except KeyError:
        #except Exception as error:
            #logger.exception('Wide exception in Password Change: %s', error)
            return render(request, 'uploader/passwordChange.html', {'error_message': True,
                                                              'message': 'Something went wrong when changing the password for the user.'})
    else:
        return render(request, 'uploader/passwordChange.html')
