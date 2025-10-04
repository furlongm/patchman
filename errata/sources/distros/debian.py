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
import re
from datetime import datetime
from debian.deb822 import Dsc
from io import StringIO

from django.db import connections

from operatingsystems.models import OSRelease
from operatingsystems.utils import get_or_create_osrelease
from packages.models import Package
from packages.utils import get_or_create_package, find_evr
from patchman.signals import error_message, pbar_start, pbar_update, warning_message
from util import get_url, fetch_content, get_setting_of_type, extract

DSCs = {}


def update_debian_errata(concurrent_processing=True):
    """ Update Debian errata using:
          https://salsa.debian.org/security-tracker-team/security-tracker/raw/master/data/DSA/list
          https://salsa.debian.org/security-tracker-team/security-tracker/raw/master/data/DSA/list
    """
    codenames = retrieve_debian_codenames()
    create_debian_os_releases(codenames)
    dsas = fetch_debian_dsa_advisories()
    dlas = fetch_debian_dla_advisories()
    advisories = dsas + dlas
    fetch_dscs_from_debian_package_file_maps()
    accepted_codenames = get_accepted_debian_codenames()
    errata = parse_debian_errata(advisories, accepted_codenames)
    create_debian_errata(errata, accepted_codenames, concurrent_processing)


def fetch_debian_dsa_advisories():
    """ Fetch the current Debian DLA file
    """
    debian_dsa_url = 'https://salsa.debian.org/security-tracker-team/security-tracker/raw/master/data/DSA/list'
    res = get_url(debian_dsa_url)
    data = fetch_content(res, 'Fetching Debian DSAs')
    return data.decode()


def fetch_debian_dla_advisories():
    """ Fetch the current Debian DSA file
    """
    debian_dsa_url = 'https://salsa.debian.org/security-tracker-team/security-tracker/raw/master/data/DLA/list'
    res = get_url(debian_dsa_url)
    data = fetch_content(res, 'Fetching Debian DLAs')
    return data.decode()


def fetch_dscs_from_debian_package_file_maps():
    """ Fetch the current Debian package file maps
    """
    repos = ['debian', 'debian-security']
    for repo in repos:
        file_map_url = f'https://deb.debian.org/{repo}/indices/package-file.map.bz2'
        res = get_url(file_map_url)
        data = fetch_content(res, f'Fetching `{repo}` package file map')
        file_map_data = extract(data, file_map_url).decode()
        parse_debian_package_file_map(file_map_data, repo)


def parse_debian_package_file_map(data, repo):
    """ Parse the a Debian package file map
        Format:
            Path: ./pool/updates/main/3/389-ds-base/389-ds-base_1.4.0.21-1+deb10u1.dsc
            Source: 389-ds-base
            Source-Version: 1.4.0.21-1+deb10u1
    """
    parsing_dsc = False
    for line in data.splitlines():
        if line.startswith('Path:'):
            if line.endswith('.dsc'):
                parsing_dsc = True
                path = line.split(' ')[1].lstrip('./')
                url = f'https://deb.debian.org/{repo}/{path}'
            else:
                parsing_dsc = False
        elif line.startswith('Source:') and parsing_dsc:
            source = line.split(' ')[1]
        elif line.startswith('Source-Version:') and parsing_dsc:
            version = line.split(' ')[1]
            if not DSCs.get(source):
                DSCs[source] = {}
            if not DSCs[source].get(version):
                DSCs[source][version] = {}
            DSCs[source][version] = {'url': url}
            parsing_dsc = False


def parse_debian_errata(advisories, accepted_codenames):
    """ Parse Debian DSA/DLA files for security advisories
    """
    distro_pattern = re.compile(r'^\t\[(.+?)\] - .*')
    title_pattern = re.compile(r'^\[(.+?)\] (.+?) (.+?)[ ]+[-]+ (.*)')
    errata = []
    e = {'packages': {}, 'cve_ids': [], 'releases': []}
    for line in advisories.splitlines():
        if line.startswith('['):
            errata = add_errata_by_codename(errata, e, accepted_codenames)
            e = {'packages': {}, 'cve_ids': [], 'releases': []}
            match = re.match(title_pattern, line)
            if match:
                e = parse_debian_erratum_advisory(e, match)
        elif line.startswith('\t{'):
            for cve_id in line.strip('\t{}').split():
                e['cve_ids'].append(cve_id)
        elif line.startswith('\t['):
            match = re.match(distro_pattern, line)
            if match:
                release = match.group(1)
                e['releases'].append(release)
                if not e.get('packages').get(release):
                    e['packages'][release] = []
                e['packages'][release].append(parse_debian_erratum_package(line, accepted_codenames))
    # add the last one
    errata = add_errata_by_codename(errata, e, accepted_codenames)
    return errata


def add_errata_by_codename(errata, e, accepted_codenames):
    """ Get errata by codename and add to errata
    """
    if e:
        for release in e.get('releases'):
            if release in accepted_codenames:
                errata.append(e)
    return errata


def parse_debian_erratum_advisory(e, match):
    """ Parse the initial details for an erratum in a DSA/DLA file
        Returns the updated dictionary
    """
    date = match.group(1)
    issue_date = int(datetime.strptime(date, '%d %b %Y').strftime('%s'))
    erratum_name = match.group(2)
    synopsis = match.group(4)
    e['name'] = erratum_name
    e['issue_date'] = issue_date
    e['synopsis'] = synopsis
    return e


def create_debian_errata(errata, accepted_codenames, concurrent_processing):
    """ Create Debian Errata
    """
    if concurrent_processing:
        create_debian_errata_concurrently(errata, accepted_codenames)
    else:
        create_debian_errata_serially(errata, accepted_codenames)


def create_debian_errata_serially(errata, accepted_codenames):
    """ Create Debian Errata Serially
    """
    elen = len(errata)
    pbar_start.send(sender=None, ptext=f'Processing {elen} Debian Errata', plen=elen)
    for i, erratum in enumerate(errata):
        process_debian_erratum(erratum, accepted_codenames)
        pbar_update.send(sender=None, index=i + 1)


def create_debian_errata_concurrently(errata, accepted_codenames):
    """ Create Debian Errata concurrently
    """
    connections.close_all()
    elen = len(errata)
    pbar_start.send(sender=None, ptext=f'Processing {elen} Debian Errata', plen=elen)
    i = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=25) as executor:
        futures = [executor.submit(process_debian_erratum, erratum, accepted_codenames) for erratum in errata]
        for future in concurrent.futures.as_completed(futures):
            i += 1
            pbar_update.send(sender=None, index=i + 1)


def process_debian_erratum(erratum, accepted_codenames):
    """ Process a single Debian Erratum
    """
    try:
        from errata.utils import get_or_create_erratum
        erratum_name = erratum.get('name')
        e, created = get_or_create_erratum(
            name=erratum_name,
            e_type='security',
            issue_date=erratum.get('issue_date'),
            synopsis=erratum.get('synopsis'),
        )
        e.add_reference('Link', f'https://security-tracker.debian.org/tracker/{erratum_name}')
        for cve_id in erratum.get('cve_ids'):
            e.add_cve(cve_id)
        for codename, packages in erratum.get('packages').items():
            if codename not in accepted_codenames:
                continue
            osrelease = OSRelease.objects.get(codename=codename)
            e.osreleases.add(osrelease)
            for package in packages:
                process_debian_erratum_fixed_packages(e, package)
    except Exception as exc:
        error_message.send(sender=None, text=exc)


def parse_debian_erratum_package(line, accepted_codenames):
    """ Parse the codename and source package from a DSA/DLA file
        Returns the source package and source version
    """
    distro_package_pattern = re.compile(r'^\t\[(.+?)\] - (.+?) (.*)')
    match = re.match(distro_package_pattern, line)
    if match:
        codename = match.group(1)
        if codename in accepted_codenames:
            source_package = match.group(2)
            source_version = match.group(3)
            fetch_debian_dsc_package_list(source_package, source_version)
            return source_package, source_version


def get_debian_dsc_package_list(package, version):
    """ Get the package list from a DSC file for a given source package/version
    """
    if not DSCs.get(package) or not DSCs[package].get(version):
        return
    package_list = DSCs[package][version].get('package_list')
    if package_list:
        return package_list


def fetch_debian_dsc_package_list(package, version):
    """ Fetch the package list from a DSC file for a given source package/version
    """
    if not DSCs.get(package) or not DSCs[package].get(version):
        warning_message.send(sender=None, text=f'No DSC found for {package} {version}')
        return
    source_url = DSCs[package][version]['url']
    res = get_url(source_url)
    data = res.content
    dsc = Dsc(data.decode())
    package_list = dsc.get('package-list')
    DSCs[package][version]['package_list'] = package_list


def get_accepted_debian_codenames():
    """ Get acceptable Debian OS codenames
        Can be overridden by specifying DEBIAN_CODENAMES in settings
    """
    default_codenames = ['bookworm', 'trixie']
    accepted_codenames = get_setting_of_type(
        setting_name='DEBIAN_CODENAMES',
        setting_type=list,
        default=default_codenames,
    )
    return accepted_codenames


def retrieve_debian_codenames():
    """ Returns the codename to version mapping
    """
    distro_info_url = 'https://debian.pages.debian.net/distro-info-data/debian.csv'
    res = get_url(distro_info_url)
    debian_csv = fetch_content(res, 'Fetching Debian distro data')
    reader = csv.DictReader(StringIO(debian_csv.decode()))
    codename_to_version = {}
    for row in reader:
        version = row.get('version')
        series = row.get('series')
        codename_to_version[series] = version
    return codename_to_version


def create_debian_os_releases(codename_to_version):
    """ Create OSReleases for acceptable Debian codenames
    """
    accepted_codenames = get_accepted_debian_codenames()
    for codename, version in codename_to_version.items():
        if codename in accepted_codenames:
            osrelease_name = f'Debian {version}'
            get_or_create_osrelease(name=osrelease_name, codename=codename)


def process_debian_erratum_fixed_packages(e, package_data):
    """ Process packages fixed in a Debian errata
    """
    source_package, source_version = package_data
    epoch, ver, rel = find_evr(source_version)
    package_list = get_debian_dsc_package_list(source_package, source_version)
    if not package_list:
        return
    fixed_packages = set()
    for package in package_list:
        if package.get('package-type') != 'deb':
            continue
        name = package.get('package')
        arches = process_debian_dsc_arches(package.get('_other'))
        for arch in arches:
            fixed_package = get_or_create_package(name, epoch, ver, rel, arch, Package.DEB)
            fixed_packages.add(fixed_package)
    e.add_fixed_packages(fixed_packages)


def process_debian_dsc_arches(arches):
    """ Process arches for dsc files
        Return a list of arches for a given package in a dsc file
    """
    arches = arches.replace('arch=', '')
    accepted_arches = []
    # https://www.debian.org/ports/
    official_ports = [
        'amd64',
        'arm64',
        'armel',
        'armhf',
        'i386',
        'mips64el',
        'ppc64el',
        'riscv64',
        's390x',
    ]
    for arch in arches.split(','):
        if arch == 'any':
            return official_ports
        elif arch == 'all':
            return ['all']  # architecture-independent packages
        elif arch in official_ports:
            accepted_arches.append(arch)
            continue
        elif arch.startswith('any-'):
            real_arch = arch.split('-')[1]
            if real_arch in official_ports:
                accepted_arches.append(real_arch)
                continue
        elif arch.endswith('-any'):
            if arch.startswith('linux'):
                return official_ports
    return accepted_arches
