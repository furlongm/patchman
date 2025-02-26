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

from django.db import transaction

from packages.models import Package
from packages.utils import get_or_create_package, parse_package_string
from util import get_url, download_url, get_setting_of_type
from patchman.signals import progress_info_s, progress_update_s


def update_alma_errata(concurrent_processing=True):
    """ Update Alma Linux advisories from errata.almalinux.org:
           https://errata.almalinux.org/8/errata.full.json
           https://errata.almalinux.org/9/errata.full.json
        and process advisories
    """
    default_alma_releases = [8, 9]
    alma_releases = get_setting_of_type(
        setting_name='ALMA_RELEASES',
        setting_type=list,
        default=default_alma_releases,
    )
    for release in alma_releases:
        advisories = download_alma_advisories(release)
        process_alma_errata(release, advisories, concurrent_processing)


def download_alma_advisories(release):
    """ Download Alma Linux advisories
    """
    alma_errata_url = f'https://errata.almalinux.org/{release}/errata.full.json'
    headers = {'Accept': 'application/json', 'Cache-Control': 'no-cache, no-tranform'}
    res = get_url(alma_errata_url, headers=headers)
    data = download_url(res, 'Downloading Alma Linux Errata:')
    advisories = json.loads(data).get('data')
    return advisories


def process_alma_errata(release, advisories, concurrent_processing):
    """ Process Alma Linux Errata
    """
    if concurrent_processing:
        process_alma_errata_concurrently(release, advisories)
    else:
        process_alma_errata_serially(release, advisories)


def process_alma_errata_serially(release, advisories):
    """ Process Alma Linux Errata serially
    """
    elen = len(advisories)
    ptext = f'Processing {elen} Alma Errata:'
    progress_info_s.send(sender=None, ptext=ptext, plen=elen)
    for i, advisory in enumerate(advisories):
        process_alma_erratum(release, advisory)
        progress_update_s.send(sender=None, index=i + 1)


def process_alma_errata_concurrently(release, advisories):
    """ Process Alma Linux Errata concurrently
    """
    elen = len(advisories)
    ptext = f'Processing {elen} Alma Errata:'
    progress_info_s.send(sender=None, ptext=ptext, plen=elen)
    i = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_alma_erratum, release, advisory) for advisory in advisories]
        for future in concurrent.futures.as_completed(futures):
            i += 1
            progress_update_s.send(sender=None, index=i + 1)


def process_alma_erratum(release, advisory):
    """ Process a single Alma Linux Erratum
    """
    from errata.utils import get_or_create_erratum
    erratum_name = advisory.get('id')
    issue_date = advisory.get('issued_date')
    synopsis = advisory.get('title')
    e_type = advisory.get('type')
    e, created = get_or_create_erratum(
        name=erratum_name,
        e_type=e_type,
        issue_date=issue_date,
        synopsis=synopsis,
    )
    add_alma_erratum_osreleases(e, release)
    add_alma_erratum_references(e, advisory)
    add_alma_erratum_packages(e, advisory)
    add_alma_erratum_modules(e, advisory)


def add_alma_erratum_osreleases(e, release):
    """ Update OS Release for Alma Linux errata
    """
    from operatingsystems.models import OSRelease
    with transaction.atomic():
        osrelease, created = OSRelease.objects.get_or_create(name=f'Alma Linux {release}')
    e.osreleases.add(osrelease)
    e.save()


def add_alma_erratum_references(e, advisory):
    """ Add references for Alma Linux errata
    """
    references = advisory.get('references')
    for reference in references:
        ref_id = reference.get('id')
        er_type = reference.get('type')
        er_url = reference.get('href')
        if er_type == 'cve':
            e.add_cve(ref_id)
            continue
        if er_type == 'self':
            er_type = ref_id.split('-')[0].upper()
        e.add_reference(er_type, er_url)


def add_alma_erratum_packages(e, advisory):
    """ Parse and add packages for Alma Linux errata
    """
    packages = advisory.get('packages')
    for package in packages:
        package_name = package.get('filename')
        if package_name:
            name, epoch, ver, rel, dist, arch = parse_package_string(package_name)
            p_type = Package.RPM
            pkg = get_or_create_package(name, epoch, ver, rel, arch, p_type)
            e.packages.add(pkg)
    e.save()


def add_alma_erratum_modules(e, advisory):
    """ Parse and add modules for Alma Linux errata
    """
    from modules.utils import get_matching_modules
    modules = advisory.get('modules')
    for module in modules:
        name = module.get('name')
        arch = module.get('arch')
        context = module.get('context')
        stream = module.get('stream')
        version = module.get('version')
        matching_modules = get_matching_modules(name, stream, version, context, arch)
        for match in matching_modules:
            for package in match.packages.all():
                e.packages.add(package)
    e.save()
