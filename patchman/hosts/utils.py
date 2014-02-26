# Copyright 2012 VPAC, http://www.vpac.org
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

from socket import gethostbyaddr, gaierror, herror

from django.db import DatabaseError

from signals import progress_info_s, progress_update_s


def update_rdns(host):
    """ Update the reverse DNS for a host
    """

    try:
        reversedns = str(gethostbyaddr(host.ipaddress)[0])
    except (gaierror, herror):
        reversedns = 'None'

    host.reversedns = reversedns
    try:
        host.save()
    except DatabaseError as e:
        print e


def remove_reports(host, timestamp):
    """ Remove all but the last 3 reports for a host
    """

    from reports.models import Report

    reports = Report.objects.filter(host=host).order_by('-created')[:3]
    report_ids = []

    for report in reports:
        report_ids.append(report.id)
        report.accessed = timestamp
        report.save()

    del_reports = Report.objects.filter(host=host).exclude(id__in=report_ids)

    rlen = del_reports.count()
    ptext = 'Cleaning %s old reports' % rlen
    progress_info_s.send(sender=None, ptext=ptext, plen=rlen)
    for i, report in enumerate(del_reports):
        report.delete()
        progress_update_s.send(sender=None, index=i + 1)
