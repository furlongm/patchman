# Django settings for patchman project.

DEBUG = False

ADMINS = (
    ('Your Name', 'you@example.com'),
)

DATABASES = {
    'default': {
#        'ENGINE': 'django.db.backends.sqlite3',  # noqa - disabled until django 5.1 is in use, see https://blog.pecar.me/django-sqlite-dblock
        'ENGINE': 'patchman.sqlite3',
        'NAME': '/var/lib/patchman/db/patchman.db',
        'OPTIONS': {
            'timeout': 30
        }
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# Create a unique string here, and don't share it with anybody.
SECRET_KEY = ''

# Add the IP addresses that your web server will be listening on,
# instead of '*'
ALLOWED_HOSTS = ['127.0.0.1', '*']

# Maximum number of mirrors to add or refresh per repo
MAX_MIRRORS = 2

# Maximum number of failures before disabling a mirror, set to -1 to never disable mirrors
MAX_MIRROR_FAILURES = 14

# Number of days to wait before raising that a host has not reported
DAYS_WITHOUT_REPORT = 14

# list of errata sources to update, remove unwanted ones to improve performance
ERRATA_OS_UPDATES = ['yum', 'rocky', 'alma', 'arch', 'ubuntu', 'debian']

# list of Alma Linux releases to update
ALMA_RELEASES = [8, 9]

# list of Debian Linux releases to update
DEBIAN_CODENAMES = ['bookworm', 'trixie']

# list of Ubuntu Linux releases to update
UBUNTU_CODENAMES = ['jammy', 'noble']

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
