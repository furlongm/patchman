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

from patchman.arch.utils import clean_architectures
from patchman.hosts.utils import clean_tags
from patchman.modules.utils import clean_modules
from patchman.packages.utils import (
    clean_packagenames, clean_packages, clean_packageupdates,
)
from patchman.repos.utils import clean_repos
from patchman.util.logging import set_quiet_mode


class Command(BaseCommand):
    help = 'Check database consistency and clean unused entries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--remove-duplicates',
            action='store_true',
            help='Remove duplicate packages (may take some time)',
        )

    def handle(self, *args, **options):
        set_quiet_mode(options['verbosity'] == 0)
        remove_duplicates = options['remove_duplicates']
        clean_packageupdates()
        clean_packages(remove_duplicates)
        clean_packagenames()
        clean_architectures()
        clean_repos()
        clean_modules()
        clean_packageupdates()
        clean_tags()
