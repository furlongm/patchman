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

from django.db import connections

from operatingsystems.utils import get_or_create_osrelease
from patchman.signals import error_message, pbar_start, pbar_update
from packages.models import Package
from packages.utils import find_evr, get_matching_packages, get_or_create_package
from util import get_url, fetch_content


def update_arch_errata(concurrent_processing=False):
    """ Update Arch Linux Errata from the following sources:
        https://security.archlinux.org/advisories.json
    """
    add_arch_linux_osrelease()
    advisories = fetch_arch_errata()
    parse_arch_errata(advisories, concurrent_processing)


def fetch_arch_errata():
    """ Fetch Arch Linux Errata Advisories
        https://security.archlinux.org/advisories.json
    """
    res = get_url('https://security.archlinux.org/advisories.json')
    advisories = fetch_content(res, 'Fetching Arch Advisories')
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
    osrelease = get_or_create_osrelease(name='Arch Linux')
    elen = len(advisories)
    pbar_start.send(sender=None, ptext=f'Processing {elen} Arch Advisories', plen=elen)
    for i, advisory in enumerate(advisories):
        process_arch_erratum(advisory, osrelease)
        pbar_update.send(sender=None, index=i + 1)


def parse_arch_errata_concurrently(advisories):
    """ Parse Arch Linux Errata Advisories concurrently
    """
    osrelease = get_or_create_osrelease(name='Arch Linux')
    connections.close_all()
    elen = len(advisories)
    pbar_start.send(sender=None, ptext=f'Processing {elen} Arch Advisories', plen=elen)
    i = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=25) as executor:
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
    get_or_create_osrelease(name='Arch Linux')


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
    data = res.content
    group = json.loads(data)
    packages = group.get('packages')

    affected = group.get('affected')
    affected_packages = find_arch_affected_packages(affected, packages)
    e.add_affected_packages(affected_packages)

    fixed = group.get('fixed')
    fixed_packages = find_arch_fixed_packages(fixed, packages)
    e.add_fixed_packages(fixed_packages)

    add_arch_erratum_group_references(e, group)
    add_arch_erratum_group_cves(e, group)


def find_arch_affected_packages(affected, packages):
    """ Find Arch Linux Erratum Affected Packages
        This checks existing packages for matches and does not
        require an architecture
    """
    package_type = Package.ARCH
    epoch, version, release = find_evr(affected)
    affected_packages = set()
    for package in packages:
        matching_packages = get_matching_packages(package, epoch, version, release, package_type)
        for match in matching_packages:
            affected_packages.add(match)
    return affected_packages


def find_arch_fixed_packages(fixed, packages):
    """ Find Arch Linux Erratum Fixed Packages
        This adds new packages with arch x86_64 only
    """
    package_type = Package.ARCH
    epoch, version, release = find_evr(fixed)
    fixed_packages = set()
    for package in packages:
        fixed_package = get_or_create_package(
            name=package,
            epoch=epoch,
            version=version,
            release=release,
            arch='x86_64',
            p_type=package_type
        )
        fixed_packages.add(fixed_package)
    return fixed_packages


def add_arch_erratum_group_references(e, group):
    """ Add Arch Linux Erratum References
    """
    references = group.get('references')
    for reference in references:
        e.add_reference('Link', reference)


def add_arch_erratum_group_cves(e, group):
    """ Add Arch Linux Erratum CVEs
    """
    cve_ids = group.get('issues')
    for cve_id in cve_ids:
        e.add_cve(cve_id)
