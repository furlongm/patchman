# Copyright 2025 Marcus Furlong <furlongm@gmail.com>
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
from django.db.models import Count

from hosts.models import Host
from util import get_datetime_now
from util.logging import info_message


@shared_task
def find_host_updates(host_id):
    """ Task to find updates for a host
    """
    host = Host.objects.get(id=host_id)
    host.find_updates()


@shared_task
def find_all_host_updates():
    """ Task to find updates for all hosts
    """
    for host in Host.objects.all():
        find_host_updates.delay(host.id)


@shared_task
def find_all_host_updates_homogenous():
    """ Task to find updates for all hosts where hosts are expected to be homogenous
    """
    updated_hosts = []
    ts = get_datetime_now()
    for host in Host.objects.all():
        if host not in updated_hosts:
            host.find_updates()
            host.updated_at = ts
            host.save()

            # only include hosts with the exact same number of packages
            filtered_hosts = Host.objects.annotate(
                packages_count=Count('packages')).filter(
                    packages_count=host.packages.count()
                )
            # and exclude hosts with the current timestamp
            filtered_hosts = filtered_hosts.exclude(updated_at=ts)

            packages = set(host.packages.all())
            repos = set(host.repos.all())
            updates = host.updates.all()

            phosts = []
            for fhost in filtered_hosts:
                frepos = set(fhost.repos.all())
                if repos != frepos:
                    continue
                fpackages = set(fhost.packages.all())
                if packages != fpackages:
                    continue
                phosts.append(fhost)

            for phost in phosts:
                phost.updates.set(updates)
                phost.updated_at = ts
                phost.save()
                updated_hosts.append(phost)
                info_message(text=f'Added the same updates to {phost}')
