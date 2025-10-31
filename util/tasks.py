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

from celery import shared_task

from arch.utils import clean_architectures
from modules.utils import clean_modules
from packages.utils import (
    clean_packagenames, clean_packages, clean_packageupdates,
)
from repos.utils import clean_repos, remove_mirror_trailing_slashes


@shared_task
def clean_database(remove_duplicate_packages=False):
    """ Task to check the database and remove orphaned objects
        Runs all clean_* functions to check database consistency
    """
    clean_packageupdates()
    clean_packages(remove_duplicates=remove_duplicate_packages)
    clean_packagenames()
    clean_architectures()
    clean_repos()
    remove_mirror_trailing_slashes()
    clean_modules()
    clean_packageupdates()
