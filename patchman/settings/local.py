# Django settings for patchman project.

import os
import site
import sys

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-development-key-change-in-production'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1']

# Application definition
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
    'taggit',
    'bootstrap3',
    'rest_framework',
    'django_filters',
    'celery',
    'django_celery_beat',
]

LOCAL_APPS = [
    'arch.apps.ArchConfig',
    'domains.apps.DomainsConfig',
    'errata.apps.ErrataConfig',
    'hosts.apps.HostsConfig',
    'modules.apps.ModulesConfig',
    'operatingsystems.apps.OperatingsystemsConfig',
    'packages.apps.PackagesConfig',
    'repos.apps.ReposConfig',
    'security.apps.SecurityConfig',
    'reports.apps.ReportsConfig',
    'util.apps.UtilConfig',
]

INSTALLED_APPS = DEFAULT_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
]

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

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'patchman.db'),
    }
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/New_York'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files
STATIC_ROOT = os.path.join(BASE_DIR, 'run/static')
STATIC_URL = '/static/'

# Media files
MEDIA_ROOT = os.path.join(BASE_DIR, 'run/media')
MEDIA_URL = '/media/'

# Email configuration (console backend for development)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Admin email
ADMINS = [('Admin', 'admin@example.com')]

# Site ID
SITE_ID = 1

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticatedOrReadOnly'],
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
}

# Taggit settings
TAGGIT_CASE_INSENSITIVE = True

# Celery settings
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'

# Login URLs
LOGIN_REDIRECT_URL = '/patchman/'
LOGOUT_REDIRECT_URL = '/patchman/login/'
LOGIN_URL = '/patchman/login/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Maximum number of mirrors to add or refresh per repo
MAX_MIRRORS = 2

# Number of days to wait before raising that a host has not reported
DAYS_WITHOUT_REPORT = 14

# Whether to run patchman under the gunicorn web server
RUN_GUNICORN = False

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Uncomment to enable redis caching for e.g. 30 seconds
# Note that the UI results may be out of date for this amount of time
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#         'LOCATION': 'redis://127.0.0.1:6379',
#         'TIMEOUT': 30,
#     }
# }

from datetime import timedelta        # noqa
from celery.schedules import crontab  # noqa
CELERY_BEAT_SCHEDULE = {
    'process_all_unprocessed_reports': {
        'task': 'reports.tasks.process_reports',
        'schedule': crontab(minute='*/5'),
     },
    'refresh_repos_daily': {
        'task': 'repos.tasks.refresh_repos',
        'schedule': crontab(hour=4, minute=00),
    },
    'update_errata_cves_cwes_every_12_hours': {
        'task': 'errata.tasks.update_errata_and_cves',
        'schedule': timedelta(hours=12),
    },
    'run_database_maintenance_daily': {
        'task': 'util.tasks.clean_database',
        'schedule': crontab(hour=6, minute=00),
    },
    'remove_old_reports': {
        'task': 'reports.tasks.remove_reports_with_no_hosts',
        'schedule': timedelta(days=7),
    },
    'find_host_updates': {
        'task': 'hosts.tasks.find_all_host_updates_homogenous',
        'schedule': timedelta(hours=24),
    },
}
