import os

DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

ADMINS = []

SECRET_KEY = os.environ['SECRET_KEY']

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ.get('DB_HOST', 'db'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

TIME_ZONE = os.environ.get('TIME_ZONE', 'UTC')

LANGUAGE_CODE = 'en-us'

MAX_MIRRORS = int(os.environ.get('MAX_MIRRORS', '2'))
MAX_MIRROR_FAILURES = int(os.environ.get('MAX_MIRROR_FAILURES', '14'))
DAYS_WITHOUT_REPORT = int(os.environ.get('DAYS_WITHOUT_REPORT', '14'))

ERRATA_OS_UPDATES = os.environ.get(
    'ERRATA_OS_UPDATES', 'yum,rocky,alma,arch,ubuntu,debian'
).split(',')

ALMA_RELEASES = [int(r) for r in os.environ.get('ALMA_RELEASES', '8,9,10').split(',')]
DEBIAN_CODENAMES = os.environ.get('DEBIAN_CODENAMES', 'bookworm,trixie').split(',')
UBUNTU_CODENAMES = os.environ.get('UBUNTU_CODENAMES', 'jammy,noble').split(',')

RUN_GUNICORN = True

_redis_host = os.environ.get('REDIS_HOST', 'redis')
_redis_port = os.environ.get('REDIS_PORT', '6379')
_redis_url = f'redis://{_redis_host}:{_redis_port}'

CELERY_BROKER_URL = f'{_redis_url}/0'
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'queue_order_strategy': 'priority',
}
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': _redis_url,
    }
}
CACHE_MIDDLEWARE_SECONDS = int(os.environ.get('CACHE_MIDDLEWARE_SECONDS', '0'))

REQUIRE_API_KEY = os.environ.get('REQUIRE_API_KEY', 'True').lower() != 'false'

from datetime import timedelta  # noqa
from celery.schedules import crontab  # noqa

CELERY_BEAT_SCHEDULE = {
    'process_all_unprocessed_reports': {
        'task': 'reports.tasks.process_reports',
        'schedule': crontab(minute='*/5'),
    },
    'refresh_repos_daily': {
        'task': 'repos.tasks.refresh_repos',
        'schedule': crontab(hour=4, minute=0),
    },
    'update_errata_cves_cwes_every_12_hours': {
        'task': 'errata.tasks.update_errata_and_cves',
        'schedule': timedelta(hours=12),
    },
    'run_database_maintenance_daily': {
        'task': 'util.tasks.clean_database',
        'schedule': crontab(hour=6, minute=0),
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

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
    },
    'loggers': {
        'urllib3': {'level': 'WARNING', 'handlers': ['console'], 'propagate': False},
        'git': {'level': 'WARNING', 'handlers': ['console'], 'propagate': False},
        'version_utils': {'level': 'WARNING', 'handlers': ['console'], 'propagate': False},
        'celery': {'level': 'WARNING', 'handlers': ['console'], 'propagate': False},
    },
}
