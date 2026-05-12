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

from patchman.management.helpers import get_hosts
from patchman.reports.tasks import remove_reports_with_no_hosts
from patchman.util.logging import set_quiet_mode


class Command(BaseCommand):
    help = 'Remove all but the last three reports per host'

    def add_arguments(self, parser):
        parser.add_argument(
            '--host',
            type=str,
            help='Only clean reports for a specific host (FQDN substring)',
        )

    def handle(self, *args, **options):
        set_quiet_mode(options['verbosity'] == 0)
        host = options['host']
        hosts = get_hosts(host, 'Cleaning Reports')
        for h in hosts:
            h.clean_reports()

        if not host:
            remove_reports_with_no_hosts()
