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

import re
from lxml import etree

from django.conf import settings
from django.db import transaction

from packages.models import Package
from packages.utils import parse_package_string, get_or_create_package
from patchman.signals import error_message, progress_info_s, progress_update_s
from util import bunzip2, get_url, download_url, get_sha1, has_setting_of_type


def update_centos_errata():
    """ Update CentOS errata from https://cefs.steve-meier.de/
    """
    data = download_centos_errata_checksum()
    expected_checksum = parse_centos_errata_checksum(data)
    data = download_centos_errata()
    actual_checksum = get_sha1(data)
    if actual_checksum != expected_checksum:
        e = 'CEFS checksum mismatch, skipping CentOS errata parsing\n'
        e += f'{actual_checksum} (actual) != {expected_checksum} (expected)'
        error_message.send(sender=None, text=e)
    else:
        if data:
            parse_centos_errata(bunzip2(data))


def download_centos_errata_checksum():
    """ Download CentOS errata checksum from https://cefs.steve-meier.de/
    """
    res = get_url('https://cefs.steve-meier.de/errata.latest.sha1')
    return download_url(res, 'Downloading CentOS Errata Checksum:')


def download_centos_errata():
    """ Download CentOS errata from https://cefs.steve-meier.de/
    """
    res = get_url('https://cefs.steve-meier.de/errata.latest.xml.bz2')
    return download_url(res, 'Downloading CentOS Errata:')


def parse_centos_errata_checksum(data):
    """ Parse the errata checksum and return the bz2 checksum
    """
    for line in data.decode('utf-8').splitlines():
        if line.endswith('errata.latest.xml.bz2'):
            return line.split()[0]


def parse_centos_errata(data):
    """ Parse CentOS errata from https://cefs.steve-meier.de/
    """
    result = etree.XML(data)
    errata_xml = result.findall('*')
    elen = len(errata_xml)
    ptext = f'Processing {elen} Errata:'
    progress_info_s.send(sender=None, ptext=ptext, plen=elen)
    for i, child in enumerate(errata_xml):
        progress_update_s.send(sender=None, index=i + 1)
        releases = get_centos_erratum_releases(child.findall('os_release'))
        if not accepted_centos_release(releases):
            continue
        e = parse_centos_errata_tag(child.tag, child.attrib)
        if e is not None:
            parse_centos_errata_children(e, child.getchildren())


def parse_centos_errata_tag(name, attribs):
    """ Parse all tags that contain errata. If the erratum already exists,
        we assume that it already has all refs, packages, releases and arches.
    """
    from errata.utils import get_or_create_erratum
    e = None
    if name.startswith('CE'):
        issue_date = attribs['issue_date']
        references = attribs['references']
        synopsis = attribs['synopsis']
        if name.startswith('CEBA'):
            e_type = 'bugfix'
        elif name.startswith('CESA'):
            e_type = 'security'
        elif name.startswith('CEEA'):
            e_type = 'enhancement'
        e, created = get_or_create_erratum(
            name=name.replace('--', ':'),
            e_type=e_type,
            issue_date=issue_date,
            synopsis=synopsis,
        )
        add_centos_erratum_references(e, references)
        return e


def add_centos_erratum_references(e, references):
    """ Add references for CentOS errata
    """
    for reference in references.split(' '):
        e.add_reference('Link', reference)


def parse_centos_errata_children(e, children):
    """ Parse errata children to obtain architecture, release and packages
    """
    from operatingsystems.models import OSRelease
    for c in children:
        if c.tag == 'os_arch':
            pass
        elif c.tag == 'os_release':
            if accepted_centos_release([c.text]):
                osrelease_name = f'CentOS {c.text}'
                with transaction.atomic():
                    osrelease, created = OSRelease.objects.get_or_create(name=osrelease_name)
                e.osreleases.add(osrelease)
        elif c.tag == 'packages':
            name, epoch, ver, rel, dist, arch = parse_package_string(c.text)
            match = re.match(r'.*el([0-9]+).*', rel)
            if match:
                release = match.group(1)
                if accepted_centos_release([release]):
                    p_type = Package.RPM
                    pkg = get_or_create_package(name, epoch, ver, rel, arch, p_type)
                    e.packages.add(pkg)


def get_centos_erratum_releases(releases_xml):
    """ Collect the releases a given erratum pertains to
    """
    releases = set()
    for release in releases_xml:
        releases.add(int(release.text))
    return releases


def accepted_centos_release(releases):
    """ Check if we accept the releases that the erratum pertains to
        If any release is accepted we return True, else False
    """
    if has_setting_of_type('MIN_CENTOS_RELEASE', int):
        min_release = settings.MIN_CENTOS_RELEASE
    else:
        min_release = 7
    acceptable_release = False
    for release in releases:
        if int(release) >= min_release:
            acceptable_release = True
    return acceptable_release
