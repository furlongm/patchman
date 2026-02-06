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


def normalize_el_osrelease(osrelease_name):
    """Normalize EL-based distros to major version only.
    e.g. 'Rocky Linux 10.1' -> 'Rocky Linux 10'
         'rocky-linux-10.1' -> 'Rocky Linux 10'
         'almalinux-10.1' -> 'Alma Linux 10'
    """
    if osrelease_name.startswith('rocky-linux-'):
        major_version = osrelease_name.split('-')[2].split('.')[0]
        return f'Rocky Linux {major_version}'
    elif osrelease_name.startswith('almalinux-'):
        major_version = osrelease_name.split('-')[1].split('.')[0]
        return f'Alma Linux {major_version}'
    elif osrelease_name in ['Amazon Linux', 'Amazon Linux AMI']:
        return 'Amazon Linux 1'

    el_distro_prefixes = [
        'Rocky Linux',
        'Alma Linux',
        'AlmaLinux',
        'CentOS',
        'RHEL',
        'Red Hat Enterprise Linux',
        'Oracle Linux',
    ]
    for prefix in el_distro_prefixes:
        if osrelease_name.startswith(prefix):
            version_part = osrelease_name[len(prefix):].strip()
            if '.' in version_part:
                major_version = version_part.split('.')[0]
                return f'{prefix} {major_version}'
    return osrelease_name


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
