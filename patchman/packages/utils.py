# Copyright 2012 VPAC, http://www.vpac.org
# Copyright 2013-2016 Marcus Furlong <furlongm@gmail.com>
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

from django.db import IntegrityError, DatabaseError, transaction
from patchman.packages.models import PackageName, Package
from patchman.arch.models import PackageArchitecture


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
        es = '{0!s}:'.format(epoch)
        e = s.index(es) + len(epoch) + 1
    except ValueError:
        e = 0
    try:
        rs = '-{0!s}'.format(release)
        r = s.index(rs)
    except ValueError:
        r = len(s)
    return s[e:r]


def get_or_create_package(name, epoch, version, release, arch, p_type):
    """ Get or create a Package object. Returns the object or None
    """
    package = None
    name = name.lower()
    if name == 'gpg-pubkey':
        return

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

    try:
        with transaction.atomic():
            packages = Package.objects.all()
            package, c = packages.get_or_create(name=p_name,
                                                arch=p_arch,
                                                epoch=epoch,
                                                version=version,
                                                release=release,
                                                packagetype=p_type)
    except IntegrityError as e:
        error_message.send(sender=None, text=e)
        package = packages.get(name=p_name,
                               arch=p_arch,
                               epoch=epoch,
                               version=version,
                               release=release,
                               packagetype=p_type)
    except DatabaseError as e:
        error_message.send(sender=None, text=e)
    return package
