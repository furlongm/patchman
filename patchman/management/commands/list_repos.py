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
from patchman.util.logging import set_quiet_mode


class Command(BaseCommand):
    help = 'List repositories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--repo',
            type=int,
            help='Only show a specific repository (by ID)',
        )

    def handle(self, *args, **options):
        set_quiet_mode(options['verbosity'] == 0)
        repos = get_repos(options['repo'], 'Printing information')
        for repo in repos:
            repo.show()
