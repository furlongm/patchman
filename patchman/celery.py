# Copyright 2019-2021 Marcus Furlong <furlongm@gmail.com>
#
# This file is part of Patchman.
#
# Patchman is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 only.
#
# Patchman is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Patchman. If not, see <http://www.gnu.org/licenses/>

import os

from celery import Celery
from celery.signals import task_prerun

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'patchman.settings')  # noqa
from django import db  # noqa
from django.conf import settings  # noqa

app = Celery('patchman')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@task_prerun.connect
def close_stale_connections(**kwargs):
    """Close stale DB connections before each task.

    Django does this automatically for HTTP requests but not for Celery
    tasks. Without this, long-lived workers hit 'server has gone away'
    (MySQL) or 'server closed the connection unexpectedly' (PostgreSQL)
    when the DB server drops idle connections.
    """
    db.close_old_connections()
