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
# along with Patchman. If not, see <http://www.gnu.org/licenses/

import concurrent.futures
from io import BytesIO
from defusedxml import ElementTree

from operatingsystems.utils import get_or_create_osrelease
from packages.models import Package
from packages.utils import get_or_create_package
from patchman.signals import pbar_start, pbar_update, error_message
from security.models import Reference
from util import extract, get_url


def extract_updateinfo(data, url, concurrent_processing=True):
    """ Parses updateinfo.xml and extracts package/errata information
    """
    extracted = extract(data, url)
    try:
        tree = ElementTree.parse(BytesIO(extracted))
        root = tree.getroot()
        elen = root.__len__()
        updates = root.findall('update')
    except ElementTree.ParseError as e:
        error_message.send(sender=None, text=f'Error parsing updateinfo file from {url} : {e}')
    if concurrent_processing:
        extract_updateinfo_concurrently(updates, elen)
    else:
        extract_updateinfo_serially(updates, elen)


def extract_updateinfo_serially(updates, elen):
    """ Parses updateinfo.xml and extracts package/errata information serially
    """
    pbar_start.send(sender=None, ptext=f'Extracting {elen} updateinfo Errata', plen=elen)
    for i, update in enumerate(updates):
        process_updateinfo_erratum(update)
        pbar_update.send(sender=None, index=i + 1)


def extract_updateinfo_concurrently(updates, elen):
    """ Parses updateinfo.xml and extracts package/errata information concurrently
    """
    pbar_start.send(sender=None, ptext=f'Extracting {elen} updateinfo Errata', plen=elen)
    i = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(process_updateinfo_erratum, update) for update in updates]
        for future in concurrent.futures.as_completed(futures):
            i += 1
            pbar_update.send(sender=None, index=i + 1)


def process_updateinfo_erratum(update):
    """ Processes a single erratum from updateinfo.xml
    """
    from errata.utils import get_or_create_erratum
    e_type = update.attrib.get('type')
    e_name = update.find('id').text
    name, ref_type, urls = get_distro_data(e_name, e_type)
    synopsis = update.find('title').text
    issue_date = update.find('issued').attrib.get('date')
    e, created = get_or_create_erratum(name, e_type, issue_date, synopsis)
    add_updateinfo_erratum_references(e, update, ref_type, urls)
    add_updateinfo_packages(e, update)
    update.clear()


def get_distro_data(name, e_type):
    """ Adds distro-specific names and references to an Erratum
    """
    urls = []
    ref_type = 'Link'
    if name.startswith('ALAS'):
        ref_type = 'Amazon Advisory'
        if name[4] == '-':
            update_path = ''
        elif name[4:6] == '2-':
            update_path = 'AL2/'
            name = name.replace('ALAS2', 'ALAS')
        elif name[4:8] == '2023':
            update_path = 'AL2023/'
            name = name.replace('ALAS2023', 'ALAS')
        urls.append(f'https://alas.aws.amazon.com/{update_path}{name}.html')
    elif name.startswith('openSUSE-SLE') or name.startswith('openSUSE'):
        ref_type = 'SUSE Advisory'
        update_type = e_type[0].upper() + 'U'
        year = name.split('-')[-2]
        number = name.split('-')[-1].zfill(4)
        identifier = f'{year}:{number}'
        prefix = f'SUSE-{update_type}'
        name = f'{prefix}-{identifier}-1'
        url_root = 'https://www.suse.com/support/update/announcement/'
        url_path = f'{year}/{prefix}-{year}{number}-'
        for i in range(1, 10):
            url = f'{url_root}{url_path}{i}'
            if Reference.objects.filter(url=url).exists():
                continue
            res = get_url(url)
            if res.status_code != 200:
                break
            urls.append(f'{url_root}{url_path}{i}')
    elif name.startswith('EL'):
        ref_type = 'Oracle Advisory'
        urls.append(f'https://linux.oracle.com/errata/{name}.html')
    elif name.startswith('RL'):
        ref_type = 'Rocky Advisory'
        urls.append(f'https://errata.rockylinux.org/{name}')
        urls.append(f'https://apollo.build.resf.org/{name}')
    return name, ref_type, urls


def add_updateinfo_erratum_references(e, update, ref_type, urls):
    """ Adds references to an Erratum
    """
    if urls:
        for url in urls:
            e.add_reference(ref_type, url)
    references = update.find('references')
    for reference in references.findall('reference'):
        if reference.attrib.get('type') == 'cve':
            cve_id = reference.attrib.get('id')
            e.add_cve(cve_id)
        else:
            ref = reference.attrib.get('href')
            e.add_reference('Link', ref)


def get_osrelease_names(e, update):
    """ Returns a list of OSRelease names for the update
        Special case for opensuse and sles which share updates/repos
    """
    osreleases = []
    release = update.find('release')
    if release is not None:
        if release.text != '0':  # alma sets this to zero for some reason
            osrelease_name = release.text
            if osrelease_name.startswith('openSUSE'):
                suse_parts = osrelease_name.split()
                if suse_parts[1] == 'Backports':
                    # e.g. openSUSE Backports SLE-15-SP6 Update
                    version_parts = suse_parts[2].split('-')
                    major_version = version_parts[1]
                    leap_minor_version = version_parts[2].replace('SP', '')
                    leap = 'openSUSE Leap ' + major_version + '.' + leap_minor_version
                    osreleases.append(leap)
                    sles_minor_version = version_parts[2]
                    sles = 'SUSE Linux Enterprise Server ' + major_version + ' ' + sles_minor_version
                    osreleases.append(sles)
                else:
                    osrelease_name = ' '.join(suse_parts[0:3])
                    osreleases.append(osrelease_name)
            elif osrelease_name.startswith('SUSE'):
                if 'openSUSE-SLE' in osrelease_name:
                    # e.g. SUSE Updates openSUSE-SLE 15.6
                    suse_parts = osrelease_name.split()
                    version = suse_parts[-1]
                    leap = 'openSUSE Leap ' + version
                    osreleases.append(leap)
                    version_parts = version.split('.')
                    major_version = version_parts[0]
                    sles_minor_version = 'SP' + version_parts[1]
                    sles = 'SUSE Linux Enterprise Server ' + major_version + ' ' + sles_minor_version
                    osreleases.append(sles)
            else:
                osreleases.append(osrelease_name)
    return osreleases


def add_updateinfo_osreleases(e, collection, osrelease_names):
    """ Adds OSRelease objects to an Erratum
        rocky and alma need some renaming
    """
    if not osrelease_names:
        collection_name = collection.find('name')
        if collection_name is not None:
            osrelease_name = collection_name.text
            osrelease_names.append(osrelease_name)
    for osrelease_name in osrelease_names:
        if osrelease_name.startswith('almalinux'):
            version = osrelease_name.split('-')[1]
            osrelease_name = 'Alma Linux ' + version
        elif osrelease_name.startswith('rocky-linux'):
            version = osrelease_name.split('-')[2]
            osrelease_name = 'Rocky Linux ' + version
        elif osrelease_name in ['Amazon Linux', 'Amazon Linux AMI']:
            osrelease_name = 'Amazon Linux 1'
        osrelease = get_or_create_osrelease(name=osrelease_name)
        e.osreleases.add(osrelease)


def add_updateinfo_packages(e, update):
    """ Adds packages to an Erratum
    """
    osrelease_names = get_osrelease_names(e, update)
    pkglist = update.find('pkglist')
    packages = set()
    for collection in pkglist.findall('collection'):
        add_updateinfo_osreleases(e, collection, osrelease_names)
        for pkg in collection.findall('package'):
            name = pkg.attrib.get('name')
            epoch = pkg.attrib.get('epoch')
            version = pkg.attrib.get('version')
            release = pkg.attrib.get('release')
            arch = pkg.attrib.get('arch')
            package = get_or_create_package(
                name=name.lower(),
                epoch=epoch,
                version=version,
                release=release,
                arch=arch,
                p_type=Package.RPM,
            )
            packages.add(package)
        e.add_fixed_packages(packages)
