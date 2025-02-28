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
from packages.models import PackageName, Package, PackageUpdate, PackageCategory, PackageString
from patchman.signals import error_message, info_message


def convert_package_to_packagestring(package):
    """ Convert a Package object to a PackageString object
    """
    name = package.name.name
    arch = package.arch.name
    if package.category:
        category = package.category.name
    else:
        category = None

    string_package = PackageString(
        name=name,
        epoch=package.epoch,
        version=package.version,
        release=package.release,
        arch=arch,
        packagetype=package.packagetype,
        category=category,
    )
    return string_package


def convert_packagestring_to_package(strpackage):
    """ Convert a PackageString object to a Package object
    """
    with transaction.atomic():
        name, created = PackageName.objects.get_or_create(name=strpackage.name.lower())
    epoch = strpackage.epoch
    version = strpackage.version
    release = strpackage.release
    with transaction.atomic():
        arch, created = PackageArchitecture.objects.get_or_create(name=strpackage.arch)
    packagetype = strpackage.packagetype
    if strpackage.category:
        with transaction.atomic():
            category, created = PackageCategory.objects.get_or_create(name=strpackage.category)
    else:
        category = None

    package, created = Package.objects.get_or_create(
          name=name,
          epoch=epoch,
          version=version,
          release=release,
          arch=arch,
          packagetype=packagetype,
          category=category,
    )
    return package


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
        es = f'{epoch}:'
        e = s.index(es) + len(epoch) + 1
    except ValueError:
        e = 0
    try:
        rs = f'-{release}'
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
    name = name.lower()
    if name == 'gpg-pubkey':
        return

    if epoch in [None, 0, '0']:
        epoch = ''

    with transaction.atomic():
        package_name, c = PackageName.objects.get_or_create(name=name)

    with transaction.atomic():
        package_arch, c = PackageArchitecture.objects.get_or_create(name=arch)

    with transaction.atomic():
        package, c = Package.objects.get_or_create(
            name=package_name,
            arch=package_arch,
            epoch=epoch,
            version=version,
            release=release,
            packagetype=p_type,
        )
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
    """ Get packages matching certain criteria
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


def clean_packageupdates():
    """ Removes PackageUpdate objects that are no longer linked to any hosts
    """
    package_updates = list(PackageUpdate.objects.all())
    for update in package_updates:
        if update.host_set.count() == 0:
            text = f'Removing unused PackageUpdate {update}'
            info_message.send(sender=None, text=text)
            update.delete()
        for duplicate in package_updates:
            if update.oldpackage == duplicate.oldpackage and update.newpackage == duplicate.newpackage and \
                    update.security == duplicate.security and update.id != duplicate.id:
                text = f'Removing duplicate PackageUpdate: {update}'
                info_message.send(sender=None, text=text)
                for host in duplicate.host_set.all():
                    host.updates.remove(duplicate)
                    host.updates.add(update)
                    host.save()
                duplicate.delete()


def clean_packages(remove_duplicates=False):
    """ Remove packages that are no longer in use
        Optionally check for duplicate packages and remove those too
    """
    packages = Package.objects.filter(
        mirror__isnull=True,
        host__isnull=True,
        erratum__isnull=True,
        module__isnull=True,
    )
    plen = packages.count()
    if plen == 0:
        info_message.send(sender=None, text='No orphaned Packages found.')
    else:
        info_message.send(sender=None, text=f'Removing {plen} orphaned Packages')
        packages.delete()
    if remove_duplicates:
        info_message.send(sender=None, text='Checking for duplicate Packages...')
        for package in Package.objects.all():
            potential_duplicates = Package.objects.filter(
                name=package.name,
                arch=package.arch,
                epoch=package.epoch,
                version=package.version,
                release=package.release,
                packagetype=package.packagetype,
            )
            if potential_duplicates.count() > 1:
                for dupe in potential_duplicates:
                    if dupe.id != package.id:
                        info_message.send(sender=None, text=f'Removing duplicate Package {dupe}')
                        dupe.delete()


def clean_packagenames():
    """ Remove package names that are no longer in use
    """
    names = PackageName.objects.filter(package__isnull=True)
    nlen = names.count()
    if nlen == 0:
        info_message.send(sender=None, text='No orphaned PackageNames found.')
    else:
        info_message.send(sender=None, text=f'Removing {nlen} orphaned PackageNames')
        names.delete()
