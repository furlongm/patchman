# Django settings for patchman project.

import os
import site
import sys

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1']

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

# SECURE_BROWSER_XSS_FILTER = True
# SECURE_CONTENT_TYPE_NOSNIFF = True
# CSRF_COOKIE_SECURE = True
# SESSION_COOKIE_SECURE = True
# X_FRAME_OPTIONS = 'DENY'

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
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

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

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticatedOrReadOnly'],  # noqa
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],        # noqa
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',            # noqa
    'PAGE_SIZE': 100,
}

TAGGIT_CASE_INSENSITIVE = True

CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'

LOGIN_REDIRECT_URL = '/patchman/'
LOGOUT_REDIRECT_URL = '/patchman/login/'
LOGIN_URL = '/patchman/login/'

# URL prefix for static files.
STATIC_URL = '/patchman/static/'

# Additional dirs where the media should be copied from
STATICFILES_DIRS = [os.path.abspath(os.path.join(BASE_DIR, 'patchman/static'))]

# Absolute path to the directory static files should be collected to.
STATIC_ROOT = '/var/lib/patchman/static/'

if sys.prefix == '/usr':
    conf_path = '/etc/patchman'
else:
    conf_path = os.path.join(sys.prefix, 'etc/patchman')
    # if sys.prefix + conf_path doesn't exist, try ./etc/patchman (source)
    if not os.path.isdir(conf_path):
        conf_path = './etc/patchman'
    # if ./etc/patchman doesn't exist, try site.getsitepackages() (pip)
    if not os.path.isdir(conf_path):
        try:
            sitepackages = site.getsitepackages()
        except AttributeError:
            # virtualenv, try site-packages in sys.path
            sp = 'site-packages'
            sitepackages = [s for s in sys.path if s.endswith(sp)][0]
        conf_path = os.path.join(sitepackages, 'etc/patchman')
local_settings = os.path.join(conf_path, 'local_settings.py')
with open(local_settings, 'r', encoding='utf_8') as ls:
    exec(compile(ls.read(), local_settings, 'exec'))

INSTALLED_APPS = DEFAULT_APPS + THIRD_PARTY_APPS + LOCAL_APPS

if RUN_GUNICORN or (len(sys.argv) > 1 and sys.argv[1] == 'runserver'):  # noqa
    LOGIN_REDIRECT_URL = '/'
    LOGOUT_REDIRECT_URL = '/login/'
    LOGIN_URL = '/login/'
    STATICFILES_DIRS = [os.path.abspath(os.path.join(BASE_DIR, 'patchman/static'))]  # noqa
    STATIC_ROOT = os.path.abspath(os.path.join(BASE_DIR, 'run/static'))
    STATIC_URL = '/static/'
    MIDDLEWARE = [
        'django.middleware.security.SecurityMiddleware',
        'whitenoise.middleware.WhiteNoiseMiddleware',
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
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'  # noqa
