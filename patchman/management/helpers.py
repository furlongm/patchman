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

from django.core.exceptions import MultipleObjectsReturned

from patchman.hosts.models import Host
from patchman.repos.models import Repository
from patchman.util.logging import info_message


def get_host(host=None, action='Performing action'):
    """Helper function to get a single host object."""
    host_obj = None
    hostdot = host + '.'
    text = f'{action} for Host {host}'

    try:
        host_obj = Host.objects.get(hostname__startswith=hostdot)
    except Host.DoesNotExist:
        try:
            host_obj = Host.objects.get(hostname__startswith=host)
        except Host.DoesNotExist:
            text = f'Host {host} does not exist'
    except MultipleObjectsReturned:
        matches = Host.objects.filter(hostname__startswith=host).count()
        text = f'{matches} Hosts match hostname "{host}"'

    info_message(text=text)
    return host_obj


def get_hosts(hosts=None, action='Performing action'):
    """Helper function to get a list of hosts."""
    host_objs = []
    if hosts:
        if isinstance(hosts, str):
            host_obj = get_host(hosts, action)
            if host_obj is not None:
                host_objs.append(host_obj)
        elif isinstance(hosts, list):
            for host in hosts:
                host_obj = get_host(host, action)
                if host_obj is not None:
                    host_objs.append(host_obj)
    else:
        text = f'{action} for all Hosts\n'
        info_message(text=text)
        host_objs = Host.objects.all()

    return host_objs


def get_repos(repo=None, action='Performing action', only_enabled=False):
    """Helper function to get a list of repos."""
    repos = []
    if repo:
        try:
            repos.append(Repository.objects.get(id=repo))
            text = f'{action} for Repo {repo}'
        except Repository.DoesNotExist:
            text = f'Repo {repo} does not exist'
    else:
        text = f'{action} for all Repos\n'
        if only_enabled:
            repos = Repository.objects.filter(enabled=True)
        else:
            repos = Repository.objects.all()

    info_message(text=text)
    return repos
