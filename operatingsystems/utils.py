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

from django.db import IntegrityError


def get_or_create_osrelease(name, cpe_name=None, codename=None):
    """ Get or create OSRelease from OS details
    """
    from operatingsystems.models import OSRelease
    osrelease = None
    updated = False
    if cpe_name:
        try:
            osrelease, created = OSRelease.objects.get_or_create(name=name, cpe_name=cpe_name)
        except IntegrityError:
            osreleases = OSRelease.objects.filter(cpe_name=cpe_name)
            if osreleases.count() == 1:
                osrelease = osreleases.first()
                osrelease.name = name
    if not osrelease and codename:
        try:
            osrelease, created = OSRelease.objects.get_or_create(name=name, codename=codename)
        except IntegrityError:
            osreleases = OSRelease.objects.filter(codename=codename)
            if osreleases.count() == 1:
                osrelease = osreleases.first()
                osrelease.name = name
                osrelease.save()
    if not osrelease:
        osrelease, created = OSRelease.objects.get_or_create(name=name)
    if cpe_name and osrelease.cpe_name != cpe_name:
        osrelease.cpe_name = cpe_name
        updated = True
    if codename and osrelease.codename != codename:
        osrelease.codename = codename
        updated = True
    if updated:
        osrelease.save()
    return osrelease


def get_or_create_osvariant(name, osrelease, codename=None, arch=None):
    """ Get or create OSVariant from OSRelease and os details
    """
    from operatingsystems.models import OSVariant
    osvariant = None
    updated = False
    try:
        osvariant, created = OSVariant.objects.get_or_create(name=name, arch=arch)
    except IntegrityError:
        osvariants = OSVariant.objects.filter(name=name)
        if osvariants.count() == 1:
            osvariant = osvariants.first()
    if osvariant.osrelease != osrelease:
        osvariant.osrelease = osrelease
        updated = True
    if arch and osvariant.arch != arch:
        osvariant.arch = arch
        updated = True
    if codename and osvariant.codename != codename:
        osvariant.codename = codename
        updated = True
    if updated:
        osvariant.save()
    return osvariant
