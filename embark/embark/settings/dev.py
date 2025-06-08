__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2025 The AMOS Projects'
__author__ = 'Benedikt Kuehne, SirGankalot, ClProsser'
__license__ = 'MIT'

from pathlib import Path
import os
import pytz

from dotenv import load_dotenv

from embark.helper import get_version_strings

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=os.path.join(BASE_DIR.parent, '.env'))
SECRET_KEY = os.environ.get('SECRET_KEY')
ALLOWED_HOSTS = ['*']

EMBA_ROOT = os.path.join(BASE_DIR.parent, 'emba')
EMBA_LOG_ROOT = os.path.join(BASE_DIR.parent, 'emba_logs')
EMBA_LOG_URL = 'emba_logs/'

DEBUG = True
DOMAIN = "embark.local"

EMAIL_ACTIVE = True
EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_FILE_PATH = os.path.join(BASE_DIR.parent, 'mail')


INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_bootstrap5',
    'django_tables2',
    'django_celery_beat',
    'mod_wsgi.server',
    'django_apscheduler',
    'uploader',
    'users',
    'reporter',
    'dashboard',
    'tracker',
    'porter',
    'updater',
    'rest_framework',
    'workers'
]

AUTH_USER_MODEL = 'users.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'embark.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates', EMBA_LOG_ROOT],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'embark.context_processor.embark_version'
            ],
        },
    },
]

CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_HTTPONLY = False  # False since we will grab it via universal-cookies

SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False

WSGI_APPLICATION = 'embark.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DATABASE_NAME'),
        'USER': os.environ.get('DATABASE_USER'),
        'PASSWORD': os.environ.get("DATABASE_PASSWORD"),
        'HOST': os.environ.get('DATABASE_HOST'),
        'PORT': os.environ.get('DATABASE_PORT'),
        'CONN_MAX_AGE': 300,
        'TEST': {'NAME': 'test_db'},
    },
}

# Logging stuff
# ERRORS/WARNINGS->console
# DEBUG->debug.log
# INFO->embark.log
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {process:d} {thread:d} {pathname} {levelname} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{asctime} {levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console_handler': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'debug_handler': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filters': ['require_debug_true'],
            'formatter': 'verbose',
            'filename': BASE_DIR / 'debug.log',
        },
        'info_handler': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'formatter': 'simple',
            'filename': BASE_DIR / 'embark.log',
        },
    },
    'loggers': {
        '': {
            'level': 'WARNING',
            'handlers': ['info_handler', 'console_handler'],
        },
        'updater': {
            'handlers': ['debug_handler', 'info_handler', 'console_handler'],
            'level': 'DEBUG',
        },
        'uploader': {
            'handlers': ['debug_handler', 'info_handler', 'console_handler'],
            'level': 'DEBUG',
        },
        'dashboard': {
            'handlers': ['debug_handler', 'info_handler', 'console_handler'],
            'level': 'DEBUG',
        },
        'users': {
            'handlers': ['debug_handler', 'info_handler', 'console_handler'],
            'level': 'DEBUG',
        },
        'reporter': {
            'handlers': ['debug_handler', 'info_handler', 'console_handler'],
            'level': 'DEBUG',
        },
        'porter': {
            'handlers': ['debug_handler', 'info_handler', 'console_handler'],
            'level': 'DEBUG',
        },
        'tracker': {
            'handlers': ['debug_handler', 'info_handler', 'console_handler'],
            'level': 'DEBUG',
        },
        'embark': {
            'handlers': ['debug_handler', 'info_handler', 'console_handler'],
            'level': 'DEBUG',
        },
        'requests': {
            'handlers': ['info_handler'],
            'level': 'INFO',
            'propagate': False,
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 4,
        },
    }
]

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = os.environ.get('TIME_ZONE', 'UTC')

USE_I18N = True

USE_L10N = True

USE_TZ = True

TIMEZONES = tuple(zip(pytz.all_timezones, pytz.all_timezones))

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR.parent, 'static')
STATICFILES_DIRS = [
    BASE_DIR / 'static/'
]
# STATICFILES_STORAGE
# STATICFILES_FINDERS

# URL of Login-Page
LOGIN_URL = ''

# URL of Logout-Page
LOGOUT_REDIRECT_URL = ''

# Added for FIle storage to get the path to save Firmware images.
MEDIA_ROOT = os.path.join(BASE_DIR.parent, 'media')
MEDIA_URL = '/media/'

# Active Firmware
ACTIVE_FW = os.path.join(MEDIA_ROOT, 'active')

REDIS_HOST = os.environ.get('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
ASGI_APPLICATION = 'embark.asgi_dev.application'

# Format string for displaying run time timestamps in the Django admin site. The default
# just adds seconds to the standard Django format, which is useful for displaying the timestamps
# for jobs that are scheduled to run on intervals of less than one minute.
#
# See https://docs.djangoproject.com/en/dev/ref/settings/#datetime-format for format string
# syntax details.
APSCHEDULER_DATETIME_FORMAT = "N j, Y, f:s a"

# Maximum run time allowed for jobs that are triggered manually via the Django admin site, which
# prevents admin site HTTP requests from timing out.
#
# Longer running jobs should probably be handed over to a background task processing library
# that supports multiple background worker processes instead (e.g. Dramatiq, Celery, Django-RQ,
# etc. See: https://djangopackages.org/grids/g/workers-queues-tasks/ for popular options).
APSCHEDULER_RUN_NOW_TIMEOUT = 25  # Seconds

# redis/channel layers setup
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
        }
    },
}
# TODO check this https://docs.djangoproject.com/en/5.1/topics/cache/
TEMP_DIR = Path("/tmp/")

VERSION = get_version_strings()

# Worker setup
WORKER_SETUP_PATH = os.path.join(BASE_DIR.parent, "WORKER_SETUP")
WORKER_SETUP_ZIP_PATH = os.path.join(BASE_DIR.parent, "WORKER_SETUP.tar.gz")
WORKER_SETUP_LOGS = os.path.join(BASE_DIR, "worker_setup.log")

# Celery task queue
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_TASK_TRACK_STARTED = True
