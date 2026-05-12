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

from patchman.security.utils import update_cves as _update_cves
from patchman.security.utils import update_cwes
from patchman.util.logging import set_quiet_mode


class Command(BaseCommand):
    help = 'Update CVEs and CWEs from cve.org'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cve',
            type=str,
            help='Only update a specific CVE (e.g. CVE-2024-1234)',
        )
        parser.add_argument(
            '--fetch-nist-data',
            action='store_true',
            help='Fetch NIST CVE data in addition to MITRE data '
                 '(rate-limited to 1 API call every 6 seconds)',
        )

    def handle(self, *args, **options):
        set_quiet_mode(options['verbosity'] == 0)
        _update_cves(options['cve'], options['fetch_nist_data'])
        update_cwes(options['cve'])
