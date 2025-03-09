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
import defusedxml.ElementTree as ET

from operatingsystems.utils import get_or_create_osrelease
from packages.models import Package
from packages.utils import get_or_create_package
from patchman.signals import pbar_start, pbar_update, error_message
from util import extract


def extract_updateinfo(data, url):
    """ Parses updateinfo.xml and extracts package/errata information
    """
    extracted = extract(data, url)
    try:
        tree = ET.parse(BytesIO(extracted))
        root = tree.getroot()
        elen = root.__len__()
        pbar_start.send(sender=None, ptext=f'Extracting {elen} updateinfo Errata', plen=elen)
        i = 0
        with concurrent.futures.ProcessPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(process_updateinfo_erratum, update) for update in root.findall('update')]
            for future in concurrent.futures.as_completed(futures):
                i += 1
                pbar_update.send(sender=None, index=i + 1)
    except ET.ParseError as e:
        error_message.send(sender=None, text=f'Error parsing updateinfo file from {url} : {e}')


def process_updateinfo_erratum(update):
    """ Processes a single erratum from updateinfo.xml
    """
    from errata.utils import get_or_create_erratum
    e_type = update.attrib.get('type')
    name = update.find('id').text
    synopsis = update.find('title').text
    issue_date = update.find('issued').attrib.get('date')
    e, created = get_or_create_erratum(name, e_type, issue_date, synopsis)
    add_updateinfo_erratum_references(e, update)
    add_updateinfo_packages(e, update)
    update.clear()


def add_updateinfo_erratum_references(e, update):
    """ Adds references to an Erratum
    """
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
        e.add_packages(packages)
