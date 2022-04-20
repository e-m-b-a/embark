# pylint: disable=R1705
import logging
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from django.contrib.auth import authenticate, login, logout, get_user
from django.contrib import messages
from django.conf import settings

from .models import User

logger = logging.getLogger('web')

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
                    return render(request, 'user/register.html',
                                    {'error_message': True, 'message': 'Passwords do not match.'})

                return render(request, 'user/login.html',
                                {'success_message': True, 'message': 'Registration successful.'})

            except KeyError:
                logger.exception('Missing keys from data- Username, password, password_confirm')
                return render(request, 'user/register.html',
                                {'error_message': True, 'message': 'User data is invalid.'})
        except Exception as error:
            logger.exception('Wide exception in Signup: %s', error)
            return render(request, 'user/register.html',
                            {'error_message': True, 'message': 'Something went wrong when signing up the user.'})
    return render(request, 'register.html')


@require_http_methods(["GET", "POST"])
def login(request):
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
                return render(request, 'user/login.html',
                                {'error_message': True, 'message': 'Username or password are wrong.'})

            logger.debug('Found user name and password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                logger.debug('User authenticated')
                login(request, user)
                logger.debug('User logged in')
                return redirect('embark-login')
            # else:
            logger.debug('User could not be authenticated')
            messages.info(request, "Invalid user data")
            return render(request, 'user/login.html', {'error_message': True, 'message': 'Invalid user data.'})
        except Exception as error:
            logger.exception('Wide exception in Signup: %s', error)
            messages.info(request, "Invalid user data")
            return render(request, 'user/login.html',
                            {'error_message': True, 'message': 'Something went wrong when signing in the user.'})
    return render(request, 'user/login.html')


# @cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='/' + settings.LOGIN_URL)
def logout(request):
    request.session.flush()
    logger.debug("Logout user %s", request.user)
    logout(request)
    return render(request, 'user/login.html', {'success_message': True, 'message': 'Logout successful.'})


@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET", "POST"])
def password_change(request):
    if request.method == "POST":
        logger.debug(request.POST)
        user = get_user(request)

        data = {k: v[0] for k, v in dict(request.POST).items()}
        logger.debug(data)
        try:
            body = {k: v[0] for k, v in dict(request.POST).items()}
            try:
                old_password = body['oldPassword']
                new_password = body['newPassword']
                confirm_password = body['confirmPassword']

                if user.check_password(old_password):
                    if old_password == new_password:
                        logger.debug('New password = old password')
                        return render(request, 'user/passwordChange.html',
                                        {'error_message': True, 'message': 'New password matches the old password'})
                    if new_password == confirm_password:
                        user.set_password(new_password)
                        user.save()
                        authenticate(request, username=user.username, password=new_password)
                        login(request, user)
                        logger.debug('New password set, user authenticated')
                        return render(request, 'user/passwordChangeDone.html',
                                        {'success_message': True, 'message': 'Password change successful.'})
                    else:
                        logger.debug('Passwords do not match')
                        return render(request, 'user/passwordChange.html',
                                        {'error_message': True, 'message': 'Passwords do not match.'})
                else:
                    logger.debug('Old password is incorrect')
                    return render(request, 'user/passwordChange.html',
                                    {'error_message': True, 'message': 'Old password is incorrect.'})
            except KeyError:
                logger.exception('Missing keys from data-passwords')
                return render(request, 'user/passwordChange.html',
                                {'error_message': True, 'message': 'Some fields are empty!'})
        except Exception as error:
            logger.exception('Wide exception in Password Change: %s', error)
            return render(request, 'user/passwordChange.html', {'error_message': True, 'message': 'Something went wrong when changing the password for the user.'})
    return render(request, 'user/passwordChange.html')


@csrf_exempt
@login_required(login_url='/' + settings.LOGIN_URL)
@require_http_methods(["GET", "POST"])
def acc_delete(request):
    if request.method == "POST":
        logger.debug('disabling account')
        user = get_user(request)
        logger.debug(' %s Account: %s disabled', datetime.now().strftime("%H:%M:%S"), user)
        user.username = user.get_username() + '_disactivated_' + datetime.now().strftime(
            "%H:%M:%S")  # workaround for not duplicating entry users_user.username
        user.is_active = False
        user.save()
        return render(request, 'user/register.html', {'success_message': True, 'message': 'Account successfully deleted.'})
    return render (request, 'user/accountDelete.html')
    


@require_http_methods(["GET"])
@login_required(login_url='/' + settings.LOGIN_URL)
def get_log(request, log_type, lines):      # FIXME update or remove
    """
    View takes a get request with following params:
    1. log_type: selector of log file (daphne, migration, mysql_db, redis_db, uwsgi, web)
    2. lines: lines in log file
    Args:
        request: HTTPRequest instance

    Returns:

    """
    log_file_list = ["daphne", "migration", "mysql_db", "redis_db", "uwsgi", "web"]
    log_file = log_file_list[int(log_type)]
    file_path = f"{settings.BASE_DIR}/logs/{log_file}.log"
    logger.info('Load log file: %s', file_path)
    try:
        with open(file_path, encoding='utf-8') as file_:
            try:
                buffer_ = 500
                lines_found = []
                block_counter = -1

                while len(lines_found) <= lines:
                    try:
                        file_.seek(block_counter * buffer_, 2)
                    except IOError:
                        file_.seek(0)
                        lines_found = file_.readlines()
                        break

                    lines_found = file_.readlines()
                    block_counter -= 1

                result = lines_found[-(lines + 1):]
            except Exception as error:
                logger.exception('Wide exception in logstreamer: %s', error)

        return render(request, 'user/log.html',
                    {'header': log_file + '.log', 'log': ''.join(result), 'username': request.user.username})
    except IOError:
        return render(request, 'user/log.html',
                    {'header': 'Error', 'log': file_path + ' not found!', 'username': request.user.username})
