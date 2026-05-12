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

from patchman.reports.models import Report
from patchman.util.logging import info_message, set_quiet_mode


class Command(BaseCommand):
    help = 'Process pending reports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--host',
            type=str,
            help='Only process reports for a specific host (FQDN substring)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Reprocess already-processed reports',
        )

    def handle(self, *args, **options):
        set_quiet_mode(options['verbosity'] == 0)
        host = options['host']
        force = options['force']

        if host:
            try:
                reports = Report.objects.filter(
                    processed=force, host=host).order_by('created')
                text = f'Processing Reports for Host {host}'
            except Report.DoesNotExist:
                text = f'No Reports exist for Host {host}'
                info_message(text=text)
                return
        else:
            text = 'Processing Reports for all Hosts'
            reports = Report.objects.filter(
                processed=force).order_by('created')

        info_message(text=text)

        for report in reports.iterator():
            report.process(find_updates=False)
