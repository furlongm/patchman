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
from hosts.utils import find_host_updates_homogenous


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
    find_host_updates_homogenous(Host.objects.all())
