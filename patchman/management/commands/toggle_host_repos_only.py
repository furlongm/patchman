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

from django.core.management.base import BaseCommand, CommandError

from patchman.management.helpers import get_hosts
from patchman.util.logging import info_message, set_quiet_mode


class Command(BaseCommand):
    help = 'Toggle host_repos_only for matching hosts'

    def add_arguments(self, parser):
        parser.add_argument(
            'host',
            type=str,
            help='Hostname or substring pattern to match',
        )
        parser.add_argument(
            '--unset',
            action='store_true',
            help='Unset host_repos_only (default is to set it)',
        )

    def handle(self, *args, **options):
        set_quiet_mode(options['verbosity'] == 0)
        host = options['host']
        if not host:
            raise CommandError('A hostname pattern is required')
        host_repos_only = not options['unset']
        toggle = 'Setting' if host_repos_only else 'Unsetting'
        matching_hosts = get_hosts(host, f'{toggle} host_repos_only')
        for h in matching_hosts:
            info_message(text=str(h))
            h.host_repos_only = host_repos_only
            h.save()
