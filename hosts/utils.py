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

from socket import gaierror, gethostbyaddr, herror

from django.db import IntegrityError, transaction
from taggit.models import Tag

from util import get_datetime_now
from util.logging import error_message, info_message


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
            host.tags.set(report.tags.split(','), clear=True)
            if report.reboot == 'True':
                host.reboot_required = True
            else:
                host.reboot_required = False
            host.save(update_fields=[
                'ipaddress', 'kernel', 'arch', 'osvariant',
                'domain', 'lastreport', 'reboot_required',
            ])
    except IntegrityError as e:
        error_message(text=e)
    if host:
        host.check_rdns()
        return host


def find_host_updates_homogenous(hosts, verbose=False):
    """ Find updates for hosts, copying updates to homogenous hosts.
        If a host has the same packages and repos as a previously
        processed host, it is given the same updates.
    """
    from hosts.models import Host

    updated_host_ids = set()
    ts = get_datetime_now()
    host_iter = hosts.iterator() if hasattr(hosts, 'iterator') else iter(hosts)
    for host in host_iter:
        if verbose:
            info_message(text=str(host))
        if host.id not in updated_host_ids:
            host.find_updates()
            if verbose:
                info_message(text='')
            host.updated_at = ts
            host.save(update_fields=['updated_at'])

            filtered_hosts = Host.objects.filter(
                packages_count=host.packages_count)
            filtered_hosts = filtered_hosts.exclude(updated_at=ts)

            package_ids = frozenset(host.packages.values_list('id', flat=True))
            repo_ids = frozenset(host.repos.values_list('id', flat=True))
            updates = list(host.updates.all())

            for fhost in filtered_hosts.iterator():
                frepo_ids = frozenset(fhost.repos.values_list('id', flat=True))
                if repo_ids != frepo_ids:
                    continue
                fpackage_ids = frozenset(fhost.packages.values_list('id', flat=True))
                if package_ids != fpackage_ids:
                    continue

                fhost.updates.set(updates)
                fhost.reboot_required = host.reboot_required
                fhost.updated_at = ts
                fhost.save(update_fields=['updated_at', 'reboot_required'])
                updated_host_ids.add(fhost.id)
                info_message(text=f'Added the same updates to {fhost}')
        elif verbose:
            info_message(text='Updates already added in this run')


def clean_tags():
    """ Delete Tags that have no Host
    """
    tags = Tag.objects.filter(
        host__isnull=True,
    )
    tlen = tags.count()
    if tlen == 0:
        info_message(text='No orphaned Tags found.')
    else:
        info_message(text=f'{tlen} orphaned Tags found.')
        tags.delete()
