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

import re
import yaml
from defusedxml import ElementTree
from io import BytesIO

from errata.sources.repos.yum import extract_updateinfo
from packages.models import Package, PackageString
from packages.utils import get_or_create_package, parse_package_string
from patchman.signals import warning_message, error_message, pbar_start, pbar_update
from repos.utils import fetch_mirror_data, update_mirror_packages
from util import extract


def get_repomd_url(mirror_url, data, url_type='primary'):
    """ Parse repomd.xml for the specified url type
        and return url, checksum and checksum type
    """
    if isinstance(data, str):
        if data.startswith('Bad repo - not in list') or data.startswith('Invalid repo'):
            return None, None, None

    ns = 'http://linux.duke.edu/metadata/repo'
    extracted = extract(data, mirror_url)
    location = None
    try:
        tree = ElementTree.parse(BytesIO(extracted))
        root = tree.getroot()
        for child in root:
            if child.attrib.get('type') == url_type:
                for grandchild in child:
                    if grandchild.tag == f'{{{ns}}}location':
                        location = grandchild.attrib.get('href')
                    if grandchild.tag == f'{{{ns}}}checksum':
                        checksum = grandchild.text
                        checksum_type = grandchild.attrib.get('type')
    except ElementTree.ParseError as e:
        error_message.send(sender=None, text=(f'Error parsing repomd from {mirror_url}: {e}'))
    if not location:
        return None, None, None
    url = str(mirror_url.rsplit('/', 2)[0]) + '/' + location
    return url, checksum, checksum_type


def extract_module_metadata(data, url, repo):
    """ Extract module metadata from a modules.yaml file
    """
    modules = set()
    extracted = extract(data, url)
    try:
        modules_yaml = yaml.safe_load_all(extracted)
    except yaml.YAMLError as e:
        error_message.send(sender=None, text=f'Error parsing modules.yaml: {e}')

    mlen = len(re.findall(r'---', yaml.dump(extracted.decode())))
    pbar_start.send(sender=None, ptext=f'Extracting {mlen} Modules ', plen=mlen)
    for i, doc in enumerate(modules_yaml):
        pbar_update.send(sender=None, index=i + 1)
        document = doc['document']
        modulemd = doc['data']
        if document == 'modulemd':
            modulemd = doc['data']
            m_name = modulemd.get('name')
            m_stream = modulemd['stream']
            m_version = modulemd.get('version')
            m_context = modulemd.get('context')
            arch = modulemd.get('arch')
            raw_packages = modulemd.get('artifacts', {}).get('rpms', '')
            # raw_profiles = list(modulemd.get('profiles', {}).keys())

            packages = set()
            p_type = Package.RPM
            for pkg_str in raw_packages:
                p_name, p_epoch, p_ver, p_rel, p_dist, p_arch = parse_package_string(pkg_str)
                package = get_or_create_package(p_name, p_epoch, p_ver, p_rel, p_arch, p_type)
                packages.add(package)

            from modules.utils import get_or_create_module
            module = get_or_create_module(m_name, m_stream, m_version, m_context, arch, repo)

            package_ids = []
            for package in packages:
                package_ids.append(package.id)
                module.packages.add(package)
            for package in module.packages.all():
                if package.id not in package_ids:
                    module.packages.remove(package)
            modules.add(module)


def extract_yum_packages(data, url):
    """ Extract package metadata from a yum primary.xml file
    """
    extracted = extract(data, url)
    ns = 'http://linux.duke.edu/metadata/common'
    packages = set()
    try:
        context = ElementTree.iterparse(BytesIO(extracted), events=('start', 'end'))
        for event, elem in context:
            if event == 'start':
                if elem.tag == f'{{{ns}}}metadata':
                    plen = int(elem.attrib.get('packages'))
                    break
        pbar_start.send(sender=None, ptext=f'Extracting {plen} Packages', plen=plen)
        i = 0
        for event, elem in context:
            if event == 'start':
                if elem.tag == f'{{{ns}}}package':
                    if elem.attrib.get('type') == 'rpm':
                        name = version = release = arch = ''
            elif event == 'end':
                if elem.tag == f'{{{ns}}}name':
                    name = elem.text.lower()
                elif elem.tag == f'{{{ns}}}arch':
                    arch = elem.text
                elif elem.tag == f'{{{ns}}}version':
                    fullversion = elem
                    epoch = fullversion.get('epoch')
                    version = fullversion.get('ver')
                    release = fullversion.get('rel')
                elif elem.tag == f'{{{ns}}}package':
                    if name and version and release and arch:
                        if epoch == '0':
                            epoch = ''
                        package = PackageString(
                            name=name,
                            epoch=epoch,
                            version=version,
                            release=release,
                            arch=arch,
                            packagetype='R',
                        )
                        packages.add(package)
                        pbar_update.send(sender=None, index=i + 1)
                        i += 1
                    else:
                        text = f'Error parsing Package: {name} {epoch} {version} {release} {arch}'
                        error_message.send(sender=None, text=text)
                elem.clear()
    except ElementTree.ParseError as e:
        error_message.send(sender=None, text=f'Error parsing yum primary.xml from {url}: {e}')
    return packages


def refresh_repomd_updateinfo(mirror, data, mirror_url):
    """ Checks for and refreshes a yum repomd updateinfo file
    """
    url, checksum, checksum_type = get_repomd_url(mirror_url, data, url_type='updateinfo')
    if not url:
        warning_message.send(sender=None, text=f'No Errata metadata found in {mirror_url}')
        return
    data = fetch_mirror_data(
        mirror=mirror,
        url=url,
        checksum=checksum,
        checksum_type=checksum_type,
        text='Fetching Errata data',
        metadata_type='updateinfo')

    if not mirror.last_access_ok:
        return

    if mirror.errata_checksum and mirror.errata_checksum == checksum:
        text = 'Mirror Errata checksum has not changed, skipping Erratum refresh'
        warning_message.send(sender=None, text=text)
        return
    else:
        mirror.errata_checksum = checksum
        mirror.save()

    extract_updateinfo(data, url)


def refresh_repomd_modules(mirror, data, mirror_url):
    """ Checks for and refreshes a yum repomd modules file
    """
    url, checksum, checksum_type = get_repomd_url(mirror_url, data, url_type='modules')
    if not url:
        warning_message.send(sender=None, text=f'No Module metadata found in {mirror_url}')
        return
    data = fetch_mirror_data(
        mirror=mirror,
        url=url,
        checksum=checksum,
        checksum_type=checksum_type,
        text='Fetching Module data',
        metadata_type='module')

    if not mirror.last_access_ok:
        return

    if mirror.modules_checksum and mirror.modules_checksum == checksum:
        text = 'Mirror Modules checksum has not changed, skipping Module refresh'
        warning_message.send(sender=None, text=text)
        return
    else:
        mirror.modules_checksum = checksum
        mirror.save()

    extract_module_metadata(data, url, mirror.repo)


def refresh_repomd_primary(mirror, data, mirror_url):
    """ Checks for and refreshes a yum repomd primary.xml file
    """
    url, checksum, checksum_type = get_repomd_url(mirror_url, data, url_type='primary')
    if not url:
        warning_message.send(sender=None, text=f'No Package metadata found in {mirror_url}')
    data = fetch_mirror_data(
        mirror=mirror,
        url=url,
        checksum=checksum,
        checksum_type=checksum_type,
        text='Fetching Package data',
        metadata_type='package')

    if not mirror.last_access_ok:
        return

    if mirror.packages_checksum and mirror.packages_checksum == checksum:
        text = 'Mirror Packages checksum has not changed, skipping Package refresh'
        warning_message.send(sender=None, text=text)
        return
    else:
        mirror.packages_checksum = checksum
        mirror.save()

    packages = extract_yum_packages(data, url)
    if packages:
        update_mirror_packages(mirror, packages)


def refresh_yum_repo(mirror, data, mirror_url, errata_only):
    """ Refresh package, module and updateinfo/errata data for a yum-style rpm Mirror
    """
    if not errata_only:
        refresh_repomd_primary(mirror, data, mirror_url)
        refresh_repomd_modules(mirror, data, mirror_url)
    refresh_repomd_updateinfo(mirror, data, mirror_url)
