import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'patchman.conf.settings'
os.environ["CELERY_LOADER"] = "django"

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
