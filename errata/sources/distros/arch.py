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

import concurrent.futures
import json

from operatingsystems.models import OSRelease, OSVariant
from packages.models import Package
from packages.utils import find_evr, get_matching_packages
from util import get_url, download_url
from patchman.signals import error_message, pbar_start, pbar_update


def update_arch_errata(concurrent_processing=False):
    """ Update Arch Linux Errata from the following sources:
        https://security.archlinux.org/advisories.json
    """
    add_arch_linux_osrelease()
    advisories = download_arch_errata()
    parse_arch_errata(advisories, concurrent_processing)


def download_arch_errata():
    """ Download Arch Linux Errata Advisories
        https://security.archlinux.org/advisories.json
    """
    res = get_url('https://security.archlinux.org/advisories.json')
    advisories = download_url(res, 'Downloading Arch Linux Advisories:')
    return json.loads(advisories)


def parse_arch_errata(advisories, concurrent_processing):
    """ Parse Arch Linux Errata Advisories
    """
    if concurrent_processing:
        parse_arch_errata_concurrently(advisories)
    else:
        parse_arch_errata_serially(advisories)


def parse_arch_errata_serially(advisories):
    """ Parse Arch Linux Errata Advisories serially
    """
    osrelease = OSRelease.objects.get(name='Arch Linux')
    elen = len(advisories)
    pbar_start.send(sender=None, ptext=f'Processing {elen} Arch Advisories', plen=elen)
    for i, advisory in enumerate(advisories):
        process_arch_erratum(advisory, osrelease)
        pbar_update.send(sender=None, index=i + 1)


def parse_arch_errata_concurrently(advisories):
    """ Parse Arch Linux Errata Advisories concurrently
    """
    osrelease = OSRelease.objects.get(name='Arch Linux')
    elen = len(advisories)
    pbar_start.send(sender=None, ptext=f'Processing {elen} Arch Advisories', plen=elen)
    i = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(process_arch_erratum, advisory, osrelease) for advisory in advisories]
        for future in concurrent.futures.as_completed(futures):
            i += 1
            pbar_update.send(sender=None, index=i + 1)


def process_arch_erratum(advisory, osrelease):
    """ Process a single Arch Linux Erratum
    """
    from errata.utils import get_or_create_erratum
    try:
        name = advisory.get('name')
        issue_date = advisory.get('date')
        package = advisory.get('package')
        issue_type = advisory.get('type')
        synopsis = f'{package} - {issue_type}'
        e, created = get_or_create_erratum(
            name=name,
            e_type='security',
            issue_date=issue_date,
            synopsis=synopsis,
        )
        e.osreleases.add(osrelease)
        add_arch_erratum_references(e, advisory)
        add_arch_erratum_packages(e, advisory)
    except Exception as exc:
        error_message.send(sender=None, text=exc)


def add_arch_linux_osrelease():
    """ Add Arch Linux OSRelease and link existing OSVariants
    """
    osrelease, created = OSRelease.objects.get_or_create(name='Arch Linux')
    osvariants = OSVariant.objects.filter(name__startswith='Arch Linux')
    for osvariant in osvariants:
        osvariant.osrelease = osrelease
        osvariant.save()


def add_arch_erratum_references(e, advisory):
    """ Add Arch Linux Erratum References
    """
    reference = advisory.get('reference')
    e.add_reference('Mailing List', reference)
    asa_id = advisory.get('name')
    url = f'https://security.archlinux.org/advisory/{asa_id}'
    e.add_reference('ASA', url)
    raw_url = f'{url}/raw'
    res = get_url(raw_url)
    data = res.content
    parse_arch_erratum_raw(e, data.decode())


def parse_arch_erratum_raw(e, data):
    """ Parse Arch Linux Erratum Raw Data for CVEs and References
    """
    in_reference_section = False
    for line in data.splitlines():
        if line.startswith('CVE-ID'):
            cve_ids = line.split(':')[1].strip().split()
            for cve_id in cve_ids:
                e.add_cve(cve_id)
        elif line.startswith('References'):
            in_reference_section = True
            continue
        if in_reference_section:
            if line.startswith('='):
                continue
            else:
                reference = line.strip()
                if reference:
                    e.add_reference('Link', reference)


def add_arch_erratum_packages(e, advisory):
    """ Add Arch Linux Erratum Packages
    """
    group_id = advisory.get('group')
    group_url = f'https://security.archlinux.org/group/{group_id}.json'
    res = get_url(group_url)
    data = download_url(res)
    group = json.loads(data)
    packages = group.get('packages')
    affected = group.get('affected')
    epoch, version, release = find_evr(affected)
    package_type = Package.ARCH
    for package in packages:
        matching_packages = get_matching_packages(package, epoch, version, release, package_type)
        if matching_packages:
            for match in matching_packages:
                e.packages.add(match)
    references = group.get('references')
    for reference in references:
        e.add_reference('Link', reference)
    cve_ids = group.get('issues')
    for cve_id in cve_ids:
        e.add_cve(cve_id)
