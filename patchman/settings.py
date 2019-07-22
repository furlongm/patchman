# Django settings for patchman project.

from __future__ import unicode_literals, absolute_import

import os
import sys

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1']

ADMINS = []

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

SITE_ID = 1

ROOT_URLCONF = 'patchman.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
            'debug': DEBUG,
        },
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/NewYork'
USE_I18N = True
USE_L10N = True
USE_TZ = False

DEFAULT_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.admindocs',
    'django.contrib.sites',
]

THIRD_PARTY_APPS = [
    'django_extensions',
    'tagging',
    'bootstrap3',
    'rest_framework',
]

LOCAL_APPS = [
    'arch.apps.ArchConfig',
    'domains.apps.DomainsConfig',
    'packages.apps.PackagesConfig',
    'operatingsystems.apps.OperatingsystemsConfig',
    'hosts.apps.HostsConfig',
    'repos.apps.ReposConfig',
    'reports.apps.ReportsConfig',
    'util.apps.UtilConfig',
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAdminUser',),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
}

try:
    from celery import Celery
except ImportError:
    USE_ASYNC_PROCESSING = False
else:
    THIRD_PARTY_APPS += ['celery']
    USE_ASYNC_PROCESSING = True
    BROKER_HOST = 'localhost'
    BROKER_PORT = 5672
    BROKER_USER = 'guest'
    BROKER_PASSWORD = 'guest'
    BROKER_VHOST = '/'

LOGIN_REDIRECT_URL = '/patchman/'
LOGOUT_REDIRECT_URL = '/patchman/login/'
LOGIN_URL = '/patchman/login/'

# URL prefix for static files.
STATIC_URL = '/patchman/static/'

# Absolute path to the directory static files should be collected to.
STATIC_ROOT = '/var/lib/patchman/static/'

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

try:
    from .local_settings import *
except ImportError:
    if sys.prefix == '/usr':
        conf_path = '/etc/patchman'
    else:
        conf_path = sys.prefix + '/etc/patchman'
    settings_file = conf_path + '/local_settings.py'
    exec(compile(open(settings_file).read(),
                 settings_file, 'exec'))

MANAGERS = ADMINS
INSTALLED_APPS = DEFAULT_APPS + THIRD_PARTY_APPS + LOCAL_APPS

if RUN_GUNICORN or (len(sys.argv) > 1 and sys.argv[1] == 'runserver'):
    LOGIN_REDIRECT_URL = '/'
    LOGOUT_REDIRECT_URL = '/login/'
    LOGIN_URL = '/login/'
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    STATIC_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, 'static'))
    STATIC_URL = '/static/'
