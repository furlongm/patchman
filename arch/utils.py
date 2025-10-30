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

from arch.models import PackageArchitecture, MachineArchitecture
from util.logging import info_message


def clean_package_architectures():
    """ Remove package architectures that are no longer in use
    """
    parches = PackageArchitecture.objects.filter(package__isnull=True)
    plen = parches.count()
    if plen == 0:
        info_message(text='No orphaned PackageArchitectures found.')
    else:
        info_message(text=f'Removing {plen} orphaned PackageArchitectures')
        parches.delete()


def clean_machine_architectures():
    """ Remove machine architectures that are no longer in use
    """
    marches = MachineArchitecture.objects.filter(
        host__isnull=True,
        repository__isnull=True,
    )
    mlen = marches.count()
    if mlen == 0:
        info_message(text='No orphaned MachineArchitectures found.')
    else:
        info_message(text=f'Removing {mlen} orphaned MachineArchitectures')
        marches.delete()


def clean_architectures():
    """ Remove architectures that are no longer in use
    """
    clean_package_architectures()
    clean_machine_architectures()
