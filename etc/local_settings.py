# Django settings for patchman project.

DEBUG = False

ADMINS = (
#    ('Your Name', 'you@example.com'),
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',  # Add 'postgresql_psycopg2', 'postgresql', 'mysql', or 'oracle'.
        'NAME': 'patchman',                    # Or path to database file if using sqlite3.
        'USER': 'patchman',                    # Not used with sqlite3.
        'PASSWORD': 'patchman',                # Not used with sqlite3.
        'HOST': '',                            # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                            # Set to empty string for default. Not used with sqlite3.
        'STORAGE_ENGINE': 'INNODB',
        'CHARSET': 'utf8'
    }
}

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

# Create a unique string here, and don't share it with anybody.
SECRET_KEY = ''

# Add the IP addresses that your web server will be listening on
ALLOWED_HOSTS = ['127.0.0.1', 'X.X.X.X']

# Maximum number of mirrors to add or refresh per repo
MAX_MIRRORS = 5

# Number of days to wait before notifying users that a host has not reported
DAYS_WITHOUT_REPORT = 14

# Whether to run patchman under the gunicorn web server
RUN_GUNICORN = False

# Enable memcached
#CACHES = {
#    'default': {
#        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
#        'LOCATION': '127.0.0.1:11211',
#    }
#}
