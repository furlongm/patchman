# Django settings for Patchman project.
from email.utils import getaddresses

import environ


env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_LOGLEVEL=(str, 'INFO'),
    DJANGO_ADMINS=(str, ''),
    DJANGO_SECRET_KEY=(str),
    DJANGO_ALLOWED_HOSTS=(list, ['*']),
    DATABASE_NAME=(str, 'patchman'),
    DATABASE_USERNAME=(str, 'patchman'),
    DATABASE_PASSWORD=(str, 'patchman'),
    DATABASE_HOST=(str),
    DATABASE_PORT=(int, 5432),
    MEMCACHED_HOST=(str, ''),
    MEMCACHED_PORT=(int, 11211)
)

DEBUG = env('DJANGO_DEBUG')
LOGLEVEL = env('DJANGO_LOGLEVEL').upper()

ADMINS = getaddresses([env('DJANGO_ADMINS')])

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': env('DATABASE_NAME'),
        'USER': env('DATABASE_USERNAME'),
        'PASSWORD': env('DATABASE_PASSWORD'),
        'HOST': env('DATABASE_HOST'),
        'PORT': env('DATABASE_PORT'),
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
TIME_ZONE = 'Europe/Athens'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# Create a unique string here, and don't share it with anybody.
SECRET_KEY = env('DJANGO_SECRET_KEY')

# Add the IP addresses that your web server will be listening on
ALLOWED_HOSTS = env('DJANGO_ALLOWED_HOSTS')

# Maximum number of mirrors to add or refresh per repo
MAX_MIRRORS = 5

# Number of days to wait before notifying users that a host has not reported
DAYS_WITHOUT_REPORT = 14

# Whether to run patchman under the gunicorn web server
RUN_GUNICORN = True

# Enable memcached
if env('MEMCACHED_HOST'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
            'LOCATION': '{}:{}'.format(
                env('MEMCACHED_HOST'),
                env('MEMCACHED_PORT'))
        }
    }
