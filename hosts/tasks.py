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

from hosts.models import Host
from util import get_datetime_now
from util.logging import info_message


@shared_task(priority=0)
def find_host_updates(host_id):
    """ Task to find updates for a host
    """
    host = Host.objects.get(id=host_id)
    host.find_updates()


@shared_task(priority=1)
def find_all_host_updates():
    """ Task to find updates for all hosts
    """
    for host in Host.objects.all().iterator():
        find_host_updates.delay(host.id)


@shared_task(priority=1)
def find_all_host_updates_homogenous():
    """ Task to find updates for all hosts where hosts are expected to be homogenous
    """
    updated_host_ids = set()
    ts = get_datetime_now()
    for host in Host.objects.all().iterator():
        if host.id not in updated_host_ids:
            host.find_updates()
            host.updated_at = ts
            host.save()

            # only include hosts with the exact same number of packages
            filtered_hosts = Host.objects.filter(
                packages_count=host.packages_count
            )
            # and exclude hosts with the current timestamp
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
                fhost.updated_at = ts
                fhost.save()
                updated_host_ids.add(fhost.id)
                info_message(text=f'Added the same updates to {fhost}')
