# Django settings for patchman project.

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEBUG = False
ALLOWED_HOSTS = ['127.0.0.1']

ADMINS = ()

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

ROOT_URLCONF = 'patchman.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
            ],
            'debug': DEBUG,
        },
    },
]

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',

)

DEFAULT_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.staticfiles',
)

THIRD_PARTY_APPS = (
    'django_extensions',
    'tagging',
    'bootstrap3',
    'rest_framework',
)

LOCAL_APPS = (
    'patchman.hosts',
    'patchman.domains',
    'patchman.operatingsystems',
    'patchman.packages',
    'patchman.repos',
    'patchman.arch',
    'patchman.reports',
    'patchman.util',
)

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAdminUser',),
    'PAGE_SIZE': 10
}

BROKER_HOST = 'localhost'
BROKER_PORT = 5672
BROKER_USER = 'guest'
BROKER_PASSWORD = 'guest'
BROKER_VHOST = '/'

try:
    import djcelery
except ImportError:
    USE_ASYNC_PROCESSING = False
else:
    THIRD_PARTY_APPS += ('djcelery',)
    USE_ASYNC_PROCESSING = True
    djcelery.setup_loader()

LOGIN_REDIRECT_URL = '/patchman/'
LOGOUT_REDIRECT_URL = '/patchman/login/'
LOGIN_URL = '/patchman/login/'

# URL prefix for static files.
STATIC_URL = '/patchman_media/'

# Additional dirs where the media should be copied from
STATICFILES_DIRS = ('/usr/share/patchman/media/',)

# Absolute path to the directory static files should be collected to.
STATIC_ROOT = '/var/lib/patchman/media/'

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

if RUN_GUNICORN:

    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

    # Static files (CSS, JavaScript, Images)
    STATIC_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, '../patchman_media'))
    STATIC_URL = '/patchman_media/'

    # Extra places for collectstatic to find static files.
    STATICFILES_DIRS = (
        os.path.abspath(os.path.join(PROJECT_ROOT, '../media')),
    )

    LOGIN_REDIRECT_URL = '/'
    LOGOUT_REDIRECT_URL = '/login/'
    LOGIN_URL = '/login/'
