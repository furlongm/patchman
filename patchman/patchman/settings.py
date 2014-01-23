# Django settings for patchman project.

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PROJECT_DIR = BASE_DIR

DEBUG = False
TEMPLATE_DEBUG = DEBUG
ALLOWED_HOSTS = ['127.0.0.1']

ADMINS = ()

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Australia/Melbourne'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-au'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/patchman_media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = '/usr/share/patchman/media/'

ROOT_URLCONF = 'patchman.urls'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'patchman.urls'

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.static',
    'django.core.context_processors.debug',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.core.context_processors.csrf',
    'django.contrib.messages.context_processors.messages',
)

#TEMPLATE_DIRS = (
#    '/usr/share/patchman/templates',
#)

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
    'south',
    'tagging',
)

LOCAL_APPS = (
    'hosts',
    'domains',
    'operatingsystems',
    'packages',
    'repos',
    'arch',
    'reports',
    'util',
)

INSTALLED_APPS = DEFAULT_APPS + THIRD_PARTY_APPS + LOCAL_APPS

BROKER_HOST = "localhost"
BROKER_PORT = 5672
BROKER_USER = "guest"
BROKER_PASSWORD = "guest"
BROKER_VHOST = "/"

try:
    import djcelery
except ImportError:
    USE_ASYNC_PROCESSING = False
else:
    INSTALLED_APPS += ('djcelery',)
    USE_ASYNC_PROCESSING = True
    djcelery.setup_loader()

execfile("/etc/patchman/settings.py")

MANAGERS = ADMINS

LOGIN_REDIRECT_URL = '/'
#LOGIN_REDIRECT_URL = '/patchman/'
#LOGIN_URL = '/patchman/accounts/login/'
