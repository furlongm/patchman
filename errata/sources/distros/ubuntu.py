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
import csv
import os
import json
from io import StringIO
from urllib.parse import urlparse

from operatingsystems.models import OSRelease, OSVariant
from packages.models import Package, PackageName
from packages.utils import get_or_create_package, parse_package_string, find_evr
from util import get_url, download_url, get_sha256, bunzip2, get_setting_of_type
from patchman.signals import error_message, progress_info_s, progress_update_s


def update_ubuntu_errata(concurrent_processing=False):
    """ Update Ubuntu errata
    """
    codenames = retrieve_ubuntu_codenames()
    create_ubuntu_os_releases(codenames)
    data = download_ubuntu_usn_db()
    if data:
        expected_checksum = download_ubuntu_usn_db_checksum()
        actual_checksum = get_sha256(data)
        if actual_checksum == expected_checksum:
            parse_usn_data(data, concurrent_processing)
        else:
            e = 'Ubuntu USN DB checksum mismatch, skipping Ubuntu errata parsing\n'
            e += f'{actual_checksum} (actual) != {expected_checksum} (expected)'
            error_message.send(sender=None, text=e)


def download_ubuntu_usn_db():
    """ Download the Ubuntu USN database
    """
    ubuntu_usn_db_json_url = 'https://usn.ubuntu.com/usn-db/database.json.bz2'
    res = get_url(ubuntu_usn_db_json_url)
    return download_url(res, 'Downloading Ubuntu Errata:')


def download_ubuntu_usn_db_checksum():
    """ Download the Ubuntu USN database checksum
    """
    ubuntu_usn_db_checksum_url = 'https://usn.ubuntu.com/usn-db/database.json.bz2.sha256'
    res = get_url(ubuntu_usn_db_checksum_url)
    return download_url(res, 'Downloading Ubuntu Errata Checksum:').decode().split()[0]


def parse_usn_data(data, concurrent_processing):
    """ Parse the Ubuntu USN data
    """
    accepted_releases = get_accepted_ubuntu_codenames()
    extracted = bunzip2(data).decode()
    advisories = json.loads(extracted)
    if concurrent_processing:
        parse_usn_data_concurrently(advisories, accepted_releases)
    else:
        parse_usn_data_serially(advisories, accepted_releases)


def parse_usn_data_serially(advisories, accepted_releases):
    """ Parse the Ubuntu USN data serially
    """
    elen = len(advisories)
    ptext = f'Processing {elen} Ubuntu Errata:'
    progress_info_s.send(sender=None, ptext=ptext, plen=elen)
    for i, (usn_id, advisory) in enumerate(advisories.items()):
        process_usn(usn_id, advisory, accepted_releases)
        progress_update_s.send(sender=None, index=i + 1)


def parse_usn_data_concurrently(advisories, accepted_releases):
    """ Parse the Ubuntu USN data concurrently
    """
    elen = len(advisories)
    ptext = f'Processing {elen} Ubuntu Errata:'
    progress_info_s.send(sender=None, ptext=ptext, plen=elen)
    i = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_usn, usn_id, advisory, accepted_releases)
                   for usn_id, advisory in advisories.items()]
        for future in concurrent.futures.as_completed(futures):
            i += 1
            progress_update_s.send(sender=None, index=i + 1)


def process_usn(usn_id, advisory, accepted_releases):
    """ Process a single USN advisory
    """
    from errata.utils import get_or_create_erratum
    try:
        affected_releases = advisory.get('releases', {}).keys()
        if not release_is_affected(affected_releases, accepted_releases):
            return
        name = f'USN-{usn_id}'
        issue_date = int(advisory.get('timestamp'))
        synopsis = advisory.get('title')
        e, created = get_or_create_erratum(
            name=name,
            e_type='security',
            issue_date=issue_date,
            synopsis=synopsis,
        )
        add_ubuntu_erratum_osreleases(
            e,
            affected_releases,
            accepted_releases,
        )
        add_ubuntu_erratum_references(e, usn_id, advisory)
        add_ubuntu_erratum_packages(e, advisory)
    except Exception as exc:
        error_message.send(sender=None, text=exc)


def add_ubuntu_erratum_osreleases(e, affected_releases, accepted_releases):
    """ Add Ubuntu erratum OSReleases
    """
    for release in affected_releases:
        if release in accepted_releases:
            osrelease = OSRelease.objects.get(codename=release)
            e.osreleases.add(osrelease)
    e.save()


def release_is_affected(affected_releases, accepted_releases):
    """ Check if release is affected by the erratum
    """
    for release in affected_releases:
        if release in accepted_releases:
            return True
    return False


def add_ubuntu_erratum_references(e, usn_id, advisory):
    """ Add Ubuntu erratum references and CVEs
    """
    usn_url = f'https://ubuntu.com/security/notices/USN-{usn_id}'
    e.add_reference('USN', usn_url)
    cve_ids = advisory.get('cves')
    if cve_ids:
        for cve_id in cve_ids:
            if cve_id.startswith('CVE'):
                e.add_cve(cve_id)
            else:
                e.add_reference('Link', cve_id)


def add_ubuntu_erratum_packages(e, advisory):
    """ Add Ubuntu erratum packages
    """
    affected_releases = advisory.get('releases')
    package_names = PackageName.objects.all()
    p_type = Package.DEB
    for release, packages in affected_releases.items():
        if release in get_accepted_ubuntu_codenames():
            arches = packages.get('archs')
            if arches:
                for arch, urls in arches.items():
                    for url in urls.get('urls'):
                        path = urlparse(url).path
                        package_name = os.path.basename(path)
                        if package_name.endswith('.deb'):
                            name, epoch, ver, rel, dist, arch = parse_package_string(package_name)
                            pkg = get_or_create_package(name, epoch, ver, rel, arch, p_type)
                            e.packages.add(pkg)
            else:
                binaries = packages.get('binaries')
                allbinaries = packages.get('allbinaries')
                for package_name, package_data in (binaries | allbinaries).items():
                    epoch, ver, rel = find_evr(package_data.get('version'))
                    try:
                        p_name = package_names.get(name=package_name)
                    except PackageName.DoesNotExist:
                        continue
                    matching_packages = Package.objects.filter(
                        name=p_name,
                        epoch=epoch,
                        version=ver,
                        release=rel,
                        packagetype=p_type,
                    )
                    for package in matching_packages:
                        e.packages.add(package)
    e.save()


def get_accepted_ubuntu_codenames():
    """ Get acceptable Ubuntu OS codenames
        Can be overridden by specifying UBUNTU_CODENAMES in settings
    """
    default_codenames = ['focal', 'jammy', 'noble']
    accepted_codenames = get_setting_of_type(
        setting_name='UBUNTU_CODENAMES',
        setting_type=list,
        default_value=default_codenames,
    )
    return accepted_codenames


def retrieve_ubuntu_codenames():
    """ Returns the codename to version mapping
    """
    distro_info_url = 'https://debian.pages.debian.net/distro-info-data/ubuntu.csv'
    res = get_url(distro_info_url)
    ubuntu_csv = download_url(res, 'Downloading Ubuntu distro info:')
    reader = csv.DictReader(StringIO(ubuntu_csv.decode()))
    codename_to_version = {}
    for row in reader:
        version = row.get('version')
        series = row.get('series')
        codename_to_version[series] = version
    return codename_to_version


def create_ubuntu_os_releases(codename_to_version):
    """ Create OSReleases for acceptable Ubuntu codenames
    """
    accepted_codenames = get_accepted_ubuntu_codenames()
    for codename, version in codename_to_version.items():
        if codename in accepted_codenames:
            osrelease_name = f'Ubuntu {version}'
            osrelease, created = OSRelease.objects.get_or_create(name=osrelease_name, codename=codename)
            for osvariant in OSVariant.objects.filter(name__startswith=osrelease_name.replace(' LTS', '')):
                osvariant.osrelease = osrelease
                osvariant.save()
