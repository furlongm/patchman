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

from socket import gethostbyaddr, gaierror, herror

from django.db import transaction, IntegrityError

from patchman.signals import error_message


def update_rdns(host):
    """ Update the reverse DNS for a host
    """
    try:
        reversedns = str(gethostbyaddr(host.ipaddress)[0])
    except (gaierror, herror):
        reversedns = 'None'

    host.reversedns = reversedns.lower()
    host.save()


def get_or_create_host(report, arch, osvariant, domain):
    """ Get or create a host from from a report
    """
    from hosts.models import Host
    if not report.host:
        try:
            report.host = str(gethostbyaddr(report.report_ip)[0])
        except herror:
            report.host = report.report_ip
        report.save()
    try:
        with transaction.atomic():
            host, created = Host.objects.get_or_create(
                hostname=report.host,
                defaults={
                    'ipaddress': report.report_ip,
                    'arch': arch,
                    'osvariant': osvariant,
                    'domain': domain,
                    'lastreport': report.created,
                }
            )
            host.ipaddress = report.report_ip
            host.kernel = report.kernel
            host.arch = arch
            host.osvariant = osvariant
            host.domain = domain
            host.lastreport = report.created
            host.tags = report.tags
            if report.reboot == 'True':
                host.reboot_required = True
            else:
                host.reboot_required = False
            host.save()
    except IntegrityError as e:
        error_message.send(sender=None, text=e)
    if host:
        host.check_rdns()
        return host
