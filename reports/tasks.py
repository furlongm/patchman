# Copyright 2012 VPAC, http://www.vpac.org
# Copyright 2013-2021 Marcus Furlong <furlongm@gmail.com>
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

from django.conf import settings

from reports.models import Report

from celery import shared_task
from celery.schedules import crontab
from patchman.celery import app

app.conf.beat_schedule = {
    'process-reports': {
        'task': 'reports.tasks.process_reports',
        'schedule': crontab(minute='*/5'),
    },
}

@shared_task
def process_report(report_id):
    report = Report.objects.get(report_id)
    report.process()


@shared_task
def process_reports():
    reports = Report.objects.all(processed=False)
    for report in reports:
        process_report.delay(report.id)
