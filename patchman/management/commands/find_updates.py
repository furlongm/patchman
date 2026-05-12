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

from django.core.management.base import BaseCommand

from patchman.hosts.utils import find_host_updates_homogenous
from patchman.management.helpers import get_hosts
from patchman.util.logging import info_message, set_quiet_mode


class Command(BaseCommand):
    help = 'Find available updates for hosts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--host',
            type=str,
            help='Only find updates for a specific host (FQDN substring)',
        )
        parser.add_argument(
            '--alt',
            action='store_true',
            help='Use alternative algorithm (faster for many homogeneous hosts)',
        )

    def handle(self, *args, **options):
        set_quiet_mode(options['verbosity'] == 0)
        hosts = get_hosts(options['host'], 'Finding updates')
        if options['alt']:
            find_host_updates_homogenous(hosts, verbose=True)
        else:
            for host in hosts:
                info_message(text=str(host))
                host.find_updates()
                info_message(text='')
