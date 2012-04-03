# Django settings for patchman project.

#from os import path as os_path
#PROJECT_DIR = os_path.abspath(os_path.split(__file__)[0])


DEBUG = False
TEMPLATE_DEBUG = DEBUG

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

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/patchman_media/'

MEDIA_ROOT = '/usr/share/patchman/media'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
#ADMIN_MEDIA_PREFIX = '/django_media/'
STATIC_URL = '/usr/lib/python2.7/site-packages/django/contrib/admin/static/'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
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
    'django.core.context_processors.debug',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.core.context_processors.csrf',
)

TEMPLATE_DIRS = (
    '/usr/share/patchman/templates',
)

INSTALLED_APPS = (
    'andsome.layout',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django_extensions',
    'andsome',
    'south',
    'tagging',
    'patchman.hosts',
    'patchman.domains',
    'patchman.operatingsystems',
    'patchman.packages',
    'patchman.repos',
    'patchman.arch',
    'patchman.reports',
    'patchman',
)

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
