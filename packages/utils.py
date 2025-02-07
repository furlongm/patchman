# Copyright 2012 VPAC, http://www.vpac.org
# Copyright 2013-2021 Marcus Furlong <furlongm@gmail.com>
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

import re

from django.core.exceptions import MultipleObjectsReturned
from django.db import IntegrityError, DatabaseError, transaction

from arch.models import PackageArchitecture
from packages.models import PackageName, Package, PackageUpdate
from patchman.signals import error_message


def find_evr(s):
    """ Given a package version string, return the epoch, version, release
    """
    epoch = find_epoch(s)
    release = find_release(s)
    version = find_version(s, epoch, release)
    return epoch, version, release


def find_release(s):
    """ Given a package version string, return the release
    """
    r = s.rpartition('-')
    if r[0] == '':
        return ''
    else:
        return r[2]


def find_epoch(s):
    """ Given a package version string, return the epoch
    """
    r = s.partition(':')
    if r[1] == '':
        return ''
    else:
        return r[0]


def find_version(s, epoch, release):
    """ Given a package version string, return the version
    """
    try:
        es = f'{epoch!s}:'
        e = s.index(es) + len(epoch) + 1
    except ValueError:
        e = 0
    try:
        rs = f'-{release!s}'
        r = s.index(rs)
    except ValueError:
        r = len(s)
    return s[e:r]


def parse_debian_package_string(pkg_str):
    """ Parse a debian package string and return
        name, epoch, ver, release, arch
    """
    parts = pkg_str.split('_')
    name = parts[0]
    full_version = parts[1]
    arch = parts[2]
    epoch, ver, rel = find_evr(full_version)
    return name, epoch, ver, rel, None, arch


def parse_redhat_package_string(pkg_str):
    """ Parse a redhat package string and return
        name, epoch, ver, release, dist, arch
    """
    rpm_pkg_re = re.compile(r'(\S+)-(?:(\d*):)?(.*)-(~?\w+)[.+]?(~?\S+)?\.(\S+)$')  # noqa
    m = rpm_pkg_re.match(pkg_str)
    if m:
        name, epoch, ver, rel, dist, arch = m.groups()
    else:
        e = f'Error parsing package string: "{pkg_str}"'
        error_message.send(sender=None, text=e)
        return
    if dist:
        rel = f'{rel}.{dist}'
    return name, epoch, ver, rel, dist, arch


def parse_package_string(pkg_str):
    """ Parse a package string and return
        name, epoch, ver, release, dist, arch
    """
    if pkg_str.endswith('.deb'):
        return parse_debian_package_string(pkg_str.removesuffix('.deb'))
    elif pkg_str.endswith('.rpm'):
        return parse_redhat_package_string(pkg_str.removesuffix('.rpm'))
    else:
        return parse_redhat_package_string(pkg_str)


def get_or_create_package(name, epoch, version, release, arch, p_type):
    """ Get or create a Package object. Returns the object. Returns None if the
        package is the pseudo package gpg-pubkey, or if it cannot create it
    """
    package = None
    name = name.lower()
    if name == 'gpg-pubkey':
        return

    if epoch in [None, 0, '0']:
        epoch = ''

    try:
        with transaction.atomic():
            package_names = PackageName.objects.all()
            p_name, c = package_names.get_or_create(name=name)
    except IntegrityError as e:
        error_message.send(sender=None, text=e)
        p_name = package_names.get(name=name)
    except DatabaseError as e:
        error_message.send(sender=None, text=e)

    package_arches = PackageArchitecture.objects.all()
    with transaction.atomic():
        p_arch, c = package_arches.get_or_create(name=arch)

    packages = Package.objects.all()
    potential_packages = packages.filter(
        name=p_name,
        arch=p_arch,
        version=version,
        release=release,
        packagetype=p_type,
    ).order_by('-epoch')
    if potential_packages.exists():
        package = potential_packages[0]
        if epoch and package.epoch != epoch:
            package.epoch = epoch
            with transaction.atomic():
                package.save()
    else:
        try:
            with transaction.atomic():
                package = packages.create(name=p_name,
                                          arch=p_arch,
                                          epoch=epoch,
                                          version=version,
                                          release=release,
                                          packagetype=p_type)
        except DatabaseError as e:
            error_message.send(sender=None, text=e)
    return package


def get_or_create_package_update(oldpackage, newpackage, security):
    """ Get or create a PackageUpdate object. Returns the object. Returns None
        if it cannot be created
    """
    updates = PackageUpdate.objects.all()
    # see if any version of this update exists
    # if it's already marked as a security update, leave it that way
    # if not, mark it as a security update if security==True
    # this could be an issue if different distros mark the same update
    # in different ways (security vs bugfix) but in reality this is not
    # very likely to happen. if it does, we err on the side of caution
    # and mark it as the security update
    try:
        update = updates.get(
            oldpackage=oldpackage,
            newpackage=newpackage
        )
    except PackageUpdate.DoesNotExist:
        update = None
    except MultipleObjectsReturned:
        e = 'Error: MultipleObjectsReturned when attempting to add package \n'
        e += f'update with oldpackage={oldpackage} | newpackage={newpackage}:'
        error_message.send(sender=None, text=e)
        updates = updates.filter(
            oldpackage=oldpackage,
            newpackage=newpackage
        )
        for update in updates:
            e = str(update)
            error_message.send(sender=None, text=e)
        return
    try:
        if update:
            if security and not update.security:
                update.security = True
                with transaction.atomic():
                    update.save()
        else:
            with transaction.atomic():
                update, c = updates.get_or_create(
                    oldpackage=oldpackage,
                    newpackage=newpackage,
                    security=security)
    except IntegrityError as e:
        error_message.send(sender=None, text=e)
        update = updates.get(oldpackage=oldpackage,
                             newpackage=newpackage,
                             security=security)
    except DatabaseError as e:
        error_message.send(sender=None, text=e)
    return update


def get_matching_packages(name, epoch, version, release, p_type):
    """ Get packges matching certain criteria
        Returns the matching packages or None
    """
    try:
        package_name = PackageName.objects.get(name=name)
    except PackageName.DoesNotExist:
        return
    if package_name:
        packages = Package.objects.filter(
            name=package_name,
            version=version,
            release=release,
            packagetype=p_type,
        )
        return packages
