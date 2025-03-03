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
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from django.db.utils import IntegrityError

from operatingsystems.models import OSRelease
from packages.models import Package
from packages.utils import get_or_create_package, find_evr
from util import get_url, download_url, get_setting_of_type
from patchman.signals import error_message, pbar_start, pbar_update


def update_debian_errata(concurrent_processing=True):
    """ Update Debian errata using:
          https://salsa.debian.org/security-tracker-team/security-tracker/raw/master/data/DSA/list
          https://salsa.debian.org/security-tracker-team/security-tracker/raw/master/data/DSA/list
    """
    codenames = retrieve_debian_codenames()
    create_debian_os_releases(codenames)
    dsas = download_debian_dsa_advisories()
    dlas = download_debian_dla_advisories()
    advisories = dsas + dlas
    accepted_codenames = get_accepted_debian_codenames()
    errata = parse_debian_errata(advisories, accepted_codenames)
    create_debian_errata(errata, accepted_codenames, concurrent_processing)


def download_debian_dsa_advisories():
    """ Download the current Debian DLA file
    """
    debian_dsa_url = 'https://salsa.debian.org/security-tracker-team/security-tracker/raw/master/data/DSA/list'
    res = get_url(debian_dsa_url)
    data = download_url(res, 'Downloading Debian DSAs')
    return data.decode()


def download_debian_dla_advisories():
    """ Download the current Debian DSA file
    """
    debian_dsa_url = 'https://salsa.debian.org/security-tracker-team/security-tracker/raw/master/data/DLA/list'
    res = get_url(debian_dsa_url)
    data = download_url(res, 'Downloading Debian DLAs')
    return data.decode()


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
                e['packages'][release].append(parse_debian_erratum_packages(line, accepted_codenames))
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
    elen = len(errata)
    pbar_start.send(sender=None, ptext=f'Processing {elen} Debian Errata', plen=elen)
    i = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=200) as executor:
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
                process_debian_erratum_affected_packages(e, package)
    except Exception as exc:
        error_message.send(sender=None, text=exc)


def parse_debian_erratum_packages(line, accepted_codenames):
    """ Parse the codename and source packages from a DSA/DLA file
        Return the DSC object
    """
    distro_package_pattern = re.compile(r'^\t\[(.+?)\] - (.+?) (.*)')
    match = re.match(distro_package_pattern, line)
    if match:
        codename = match.group(1)
        if codename in accepted_codenames:
            source_package = match.group(2)
            source_version = match.group(3)
            return [codename, source_package, source_version]


@retry(
    retry=retry_if_exception_type(ConnectionError),
    stop=stop_after_attempt(10),
    wait=wait_exponential(multiplier=1, min=2, max=15),
)
def download_debian_package_dsc(codename, package, version):
    """ Download a DSC file for the given source package
        From this we can determine which packages are built from
        a given source package
    """
    dsc_pattern = re.compile(r'.*"(http.*dsc)"')
    source_url = f'https://packages.debian.org/source/{codename}/{package}'
    res = get_url(source_url)
    data = res.content
    dscs = re.findall(dsc_pattern, data.decode())
    if dscs:
        dsc_url = dscs[0]
        res = get_url(dsc_url)
        data = res.content
        return Dsc(data.decode())


def get_accepted_debian_codenames():
    """ Get acceptable Debian OS codenames
        Can be overridden by specifying DEBIAN_CODENAMES in settings
    """
    default_codenames = ['bookworm', 'bullseye']
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
    debian_csv = download_url(res, 'Downloading Debian distro data')
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
            try:
                osrelease, created = OSRelease.objects.get_or_create(name=osrelease_name, codename=codename)
            except IntegrityError:
                osreleases = OSRelease.objects.filter(name=osrelease_name)
                if osreleases.count() == 1:
                    osrelease = osreleases[0]
                    osrelease.codename = codename
                    osrelease.save()


def process_debian_erratum_affected_packages(e, package_data):
    """ Process packages affected by Debian errata
    """
    codename, source_package, source_version = package_data
    dsc = download_debian_package_dsc(codename, source_package, source_version)
    if not dsc:
        return
    epoch, ver, rel = find_evr(str(dsc.get_version()))
    package_list = dsc.get('package-list')
    for line in package_list.splitlines():
        if not line:
            continue
        line_parts = line.split()
        if line_parts[1] != 'deb':
            continue
        name = line_parts[0]
        arches = process_debian_dsc_arches(line_parts[4])
        for arch in arches:
            package = get_or_create_package(name, epoch, ver, rel, arch, Package.DEB)
            e.packages.add(package)


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
        'all',  # architecture-independent packages
    ]
    for arch in arches.split(','):
        if arch == 'any':
            return official_ports
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
