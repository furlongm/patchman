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

from celery import shared_task

from django.db.utils import OperationalError

from hosts.models import Host
from reports.models import Report
from util import info_message


@shared_task(bind=True, autoretry_for=(OperationalError,), retry_backoff=True, retry_kwargs={'max_retries': 5})
def process_report(self, report_id):
    """ Task to process a single report
    """
    report = Report.objects.get(id=report_id)
    report.process()


@shared_task
def process_reports():
    """ Task to process all unprocessed reports
    """
    reports = Report.objects.filter(processed=False)
    for report in reports:
        process_report.delay(report.id)


@shared_task
def clean_reports_with_no_hosts():
    """ Task to clean processed reports where the host no longer exists
    """
    for report in Report.objects.filter(processed=True):
        if not Host.objects.filter(hostname=report.host).exists():
            text = f'Deleting report {report.id} for Host `{report.host}` as the host no longer exists'
            info_message.send(sender=None, text=text)
            report.delete()
