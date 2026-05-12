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

from patchman.errata.tasks import update_errata as _update_errata
from patchman.errata.utils import (
    enrich_errata, mark_errata_security_updates,
    scan_package_updates_for_affected_packages,
)
from patchman.util import get_setting_of_type
from patchman.util.logging import set_quiet_mode


class Command(BaseCommand):
    help = 'Update errata from configured sources'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            dest='erratum_type',
            help='Only update a specific erratum type (e.g. yum, ubuntu, arch)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force refresh even if checksums match',
        )
        parser.add_argument(
            '--repo',
            type=int,
            help='Only update errata for a specific repository (by ID)',
        )

    def handle(self, *args, **options):
        set_quiet_mode(options['verbosity'] == 0)
        concurrent = get_setting_of_type(
            setting_name='CONCURRENT_PROCESSING',
            setting_type=bool,
            default=True,
        )
        max_workers = get_setting_of_type(
            setting_name='CONCURRENT_WORKERS',
            setting_type=int,
            default=25,
        )
        _update_errata(
            options['erratum_type'], options['force'], options['repo'],
        )
        scan_package_updates_for_affected_packages()
        mark_errata_security_updates(concurrent, max_workers)
        enrich_errata(concurrent, max_workers)
