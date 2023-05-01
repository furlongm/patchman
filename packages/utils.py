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
from defusedxml.lxml import _etree as etree

from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.db import IntegrityError, DatabaseError, transaction

from util import bunzip2, get_url, download_url, get_sha1
from packages.models import ErratumReference, PackageName, \
    Package, PackageUpdate
from arch.models import MachineArchitecture, PackageArchitecture
from patchman.signals import error_message, progress_info_s, progress_update_s


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


def parse_package_string(pkg_str):
    """ Parse a package string and return
        name, epoch, ver, release, dist, arch
    """

    for suffix in ['rpm', 'deb']:
        pkg_str = re.sub(f'.{suffix}$', '', pkg_str)
    pkg_re = re.compile('(\S+)-(?:(\d*):)?(.*)-(~?\w+)[.+]?(~?\S+)?\.(\S+)$')  # noqa
    m = pkg_re.match(pkg_str)
    if m:
        name, epoch, ver, rel, dist, arch = m.groups()
    else:
        e = f'Error parsing package string: "{pkg_str}"'
        error_message.send(sender=None, text=e)
        return
    if dist:
        rel = f'{rel}.{dist}'
    return name, epoch, ver, rel, dist, arch


def update_errata(force=False):
    """ Update CentOS errata from https://cefs.steve-meier.de/
        and mark packages that are security updates
    """
    data = download_errata_checksum()
    expected_checksum = parse_errata_checksum(data)
    data = download_errata()
    actual_checksum = get_sha1(data)
    if actual_checksum != expected_checksum:
        e = 'CEFS checksum did not match, skipping errata parsing'
        error_message.send(sender=None, text=e)
    else:
        if data:
            parse_errata(bunzip2(data), force)


def download_errata_checksum():
    """ Download CentOS errata checksum from https://cefs.steve-meier.de/
    """
    res = get_url('https://cefs.steve-meier.de/errata.latest.sha1')
    return download_url(res, 'Downloading Errata Checksum:')


def download_errata():
    """ Download CentOS errata from https://cefs.steve-meier.de/
    """
    res = get_url('https://cefs.steve-meier.de/errata.latest.xml.bz2')
    return download_url(res, 'Downloading CentOS Errata:')


def parse_errata_checksum(data):
    """ Parse the errata checksum and return the bz2 checksum
    """
    for line in data.decode('utf-8').splitlines():
        if line.endswith('errata.latest.xml.bz2'):
            return line.split()[0]


def parse_errata(data, force):
    """ Parse CentOS errata from https://cefs.steve-meier.de/
    """
    result = etree.XML(data)
    errata_xml = result.findall('*')
    elen = len(errata_xml)
    ptext = f'Processing {elen!s} Errata:'
    progress_info_s.send(sender=None, ptext=ptext, plen=elen)
    for i, child in enumerate(errata_xml):
        progress_update_s.send(sender=None, index=i + 1)
        if not check_centos_release(child.findall('os_release')):
            continue
        e = parse_errata_tag(child.tag, child.attrib, force)
        if e is not None:
            parse_errata_children(e, child.getchildren())


def parse_errata_tag(name, attribs, force):
    """ Parse all tags that contain errata. If the erratum already exists,
        we assume that it already has all refs, packages, releases and arches.
    """
    e = None
    if name.startswith('CE'):
        issue_date = attribs['issue_date']
        references = attribs['references']
        synopsis = attribs['synopsis']
        if name.startswith('CEBA'):
            etype = 'bugfix'
        elif name.startswith('CESA'):
            etype = 'security'
        elif name.startswith('CEEA'):
            etype = 'enhancement'
        e = create_erratum(name=name,
                           etype=etype,
                           issue_date=issue_date,
                           synopsis=synopsis,
                           force=force)
        if e is not None:
            add_erratum_refs(e, references)
    return e


def parse_errata_children(e, children):
    """ Parse errata children to obtain architecture, release and packages
    """
    for c in children:
        if c.tag == 'os_arch':
            m_arches = MachineArchitecture.objects.all()
            with transaction.atomic():
                m_arch, c = m_arches.get_or_create(name=c.text)
            e.arches.add(m_arch)
        elif c.tag == 'os_release':
            from operatingsystems.models import OSGroup
            osgroups = OSGroup.objects.all()
            osgroup_name = f'CentOS {c.text!s}'
            with transaction.atomic():
                osgroup, c = osgroups.get_or_create(name=osgroup_name)
            e.releases.add(osgroup)
        elif c.tag == 'packages':
            pkg_str = c.text.replace('.rpm', '')
            pkg_re = re.compile('(\S+)-(?:(\d*):)?(.*)-(~?\w+)[.+]?(~?\S+)?\.(\S+)$')  # noqa
            m = pkg_re.match(pkg_str)
            if m:
                name, epoch, ver, rel, dist, arch = m.groups()
            else:
                e = 'Error parsing errata: '
                e += f'could not parse package "{pkg_str!s}"'
                error_message.send(sender=None, text=e)
                continue
            if dist:
                rel = f'{rel!s}.{dist!s}'
            p_type = Package.RPM
            pkg = get_or_create_package(name, epoch, ver, rel, arch, p_type)
            e.packages.add(pkg)


def check_centos_release(releases_xml):
    """ Check if we care about the release that the erratum affects
    """
    releases = set()
    for release in releases_xml:
        releases.add(int(release.text))
    if hasattr(settings, 'MIN_CENTOS_RELEASE') and \
            isinstance(settings.MIN_CENTOS_RELEASE, int):
        min_release = settings.MIN_CENTOS_RELEASE
    else:
        # defaults to CentOS 6
        min_release = 6
    wanted_release = False
    for release in releases:
        if release >= min_release:
            wanted_release = True
    return wanted_release


def create_erratum(name, etype, issue_date, synopsis, force=False):
    """ Create an Erratum object. Returns the object or None if it already
        exists. To force update the erratum, set force=True
    """
    from packages.models import Erratum
    errata = Erratum.objects.all()
    with transaction.atomic():
        e, c = errata.get_or_create(name=name,
                                    etype=etype,
                                    issue_date=issue_date,
                                    synopsis=synopsis)
    if c or force:
        return e


def add_erratum_refs(e, references):
    """ Add references to an Erratum object
    """
    for reference in references.split(' '):
        erratarefs = ErratumReference.objects.all()
        with transaction.atomic():
            er, c = erratarefs.get_or_create(url=reference)
        e.references.add(er)


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


def mark_errata_security_updates():
    """ For each set of erratum packages, modify any PackageUpdate that
        should be marked as a security update.
    """
    package_updates = PackageUpdate.objects.all()
    from packages.models import Erratum
    errata = Erratum.objects.all()
    elen = Erratum.objects.count()
    ptext = f'Scanning {elen!s} Errata:'
    progress_info_s.send(sender=None, ptext=ptext, plen=elen)
    for i, erratum in enumerate(errata):
        progress_update_s.send(sender=None, index=i + 1)
        if erratum.etype == 'security':
            for package in erratum.packages.all():
                affected_updates = package_updates.filter(
                    newpackage=package,
                    security=False
                )
                for affected_update in affected_updates:
                    if not affected_update.security:
                        affected_update.security = True
                        try:
                            with transaction.atomic():
                                affected_update.save()
                        except IntegrityError as e:
                            error_message.send(sender=None, text=e)
                            # a version of this update already exists that is
                            # marked as a security update, so delete this one
                            affected_update.delete()
