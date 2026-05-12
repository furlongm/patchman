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

from patchman.management.helpers import get_repos
from patchman.util.logging import info_message, set_quiet_mode


class Command(BaseCommand):
    help = 'Refresh metadata for enabled repositories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--repo',
            type=int,
            help='Only refresh a specific repository (by ID)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Ignore stored checksums and force-refresh all mirrors',
        )

    def handle(self, *args, **options):
        set_quiet_mode(options['verbosity'] == 0)
        repos = get_repos(options['repo'], 'Refreshing metadata', True)
        for repo in repos:
            info_message(text=f'Repository {repo.id} : {repo}')
            repo.refresh(options['force'])
            info_message(text='')
