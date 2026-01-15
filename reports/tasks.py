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
from django.core.cache import cache
from django.db.utils import OperationalError

from hosts.models import Host
from reports.models import Report
from util.logging import info_message, warning_message


@shared_task(
    bind=True,
    priority=0,
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 5}
)
def process_report(self, report_id):
    """ Task to process a single report
    """
    report = Report.objects.get(id=report_id)
    report_id_lock_key = f'process_report_id_lock_{report_id}'
    if report.host:
        report_host_lock_key = f'process_report_host_lock_{report.host}'
    else:
        report_host_lock_key = f'process_report_host_lock_{report.report_ip}'
    # locks will expire after 2 hours
    lock_expire = 60 * 60 * 2

    if cache.add(report_id_lock_key, 'true', lock_expire):
        try:
            processing_report_id = cache.get(report_host_lock_key)
            if processing_report_id:
                if processing_report_id > report.id:
                    warning_message(f'Currently processing a newer report for {report.host} or {report.report_ip}, \
                                      marking report {report.id} as processed.')
                    report.processed = True
                    report.save()
                else:
                    warning_message(f'Currently processing an older report for {report.host} or {report.report_ip}, \
                                      will skip processing this report.')
            else:
                try:
                    cache.set(report_host_lock_key, report.id, lock_expire)
                    report.process()
                finally:
                    cache.delete(report_host_lock_key)
        finally:
            cache.delete(report_id_lock_key)
    else:
        warning_message(f'Already processing report {report_id}, skipping task.')


@shared_task(priority=1)
def process_reports():
    """ Task to process all unprocessed reports
    """
    reports = Report.objects.filter(processed=False)
    for report in reports:
        process_report.delay(report.id)


@shared_task(priority=2)
def remove_reports_with_no_hosts():
    """ Task to remove processed reports where the host no longer exists
    """
    for report in Report.objects.filter(processed=True):
        if not Host.objects.filter(hostname=report.host).exists():
            text = f'Deleting report {report.id} for Host `{report.host}` as the host no longer exists'
            info_message(text=text)
            report.delete()
