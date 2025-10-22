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

import git
import os
import shutil
import tarfile
import tempfile
from defusedxml import ElementTree
from fnmatch import fnmatch
from io import BytesIO
from pathlib import Path

from packages.models import PackageString
from packages.utils import find_evr
from patchman.signals import info_message, warning_message, error_message, pbar_start, pbar_update
from repos.utils import add_mirrors_from_urls, mirror_checksum_is_valid, update_mirror_packages
from util import extract, get_url, get_datetime_now, get_checksum, Checksum, fetch_content, response_is_valid


def refresh_gentoo_main_repo(repo):
    """ Refresh all mirrors of the main gentoo repo
    """
    mirrors = get_gentoo_mirror_urls()
    add_mirrors_from_urls(repo, mirrors)
    ts = get_datetime_now()
    for mirror in repo.mirror_set.filter(mirrorlist=False, refresh=True, enabled=True):
        if mirror.url == 'https://api.gentoo.org/mirrors/distfiles.xml':
            mirror.mirrorlist = True
            mirror.save()
            continue

        res = get_url(mirror.url + '.md5sum')
        data = fetch_content(res, 'Fetching Repo checksum')
        if data is None:
            mirror.fail()
            continue

        checksum = data.decode().split()[0]
        if checksum is None:
            mirror.fail()
            continue

        if mirror.packages_checksum == checksum:
            text = 'Mirror checksum has not changed, not refreshing Package metadata'
            warning_message.send(sender=None, text=text)
            continue

        res = get_url(mirror.url)
        mirror.last_access_ok = response_is_valid(res)
        if not mirror.last_access_ok:
            mirror.fail()
            continue

        data = fetch_content(res, 'Fetching Repo data')
        if data is None:
            mirror.fail()
            continue
        extracted = extract(data, mirror.url)
        info_message.send(sender=None, text=f'Found Gentoo Repo - {mirror.url}')

        computed_checksum = get_checksum(data, Checksum.md5)
        if not mirror_checksum_is_valid(computed_checksum, checksum, mirror, 'package'):
            mirror.fail()
            continue
        else:
            mirror.packages_checksum = checksum

        packages = extract_gentoo_packages(mirror, extracted)
        if packages:
            update_mirror_packages(mirror, packages)

        mirror.timestamp = ts
        mirror.save()


def refresh_gentoo_overlay_repo(repo):
    """ Refresh all mirrors of a Gentoo overlay repo
    """
    mirrors = get_gentoo_overlay_mirrors(repo.repo_id)
    add_mirrors_from_urls(repo, mirrors)
    ts = get_datetime_now()
    for mirror in repo.mirror_set.filter(mirrorlist=False, refresh=True, enabled=True):
        # FIXME: need to check for failure
        packages = extract_gentoo_overlay_packages(mirror)
        if packages:
            update_mirror_packages(mirror, packages)
        mirror.timestamp = ts
        mirror.save()


def get_gentoo_ebuild_keywords(content):
    """ Get the keywords for an ebuild
    """
    keywords = set()
    default_keywords = {
        'alpha',
        'amd64',
        'arm',
        'arm64',
        'hppa',
        'loong',
        'm68k',
        'mips',
        'ppc',
        'ppc64',
        'riscv',
        's390',
        'sparc',
        'x86',
    }
    for line in content.decode().splitlines():
        if not line.startswith('KEYWORDS='):
            continue
        all_keywords = line.split('=')[1].split('#')[0].strip(' "').split()
        if len(all_keywords) == 0 or '*' in all_keywords:
            all_keywords = default_keywords
        for keyword in all_keywords:
            if keyword.startswith('~'):
                continue
            if keyword.startswith('-'):
                keyword = keyword.replace('-', '')
                if keyword in all_keywords:
                    all_keywords.remove(keyword)
                continue
            keywords.add(keyword)
        break
    if keywords:
        return keywords
    else:
        return default_keywords


def get_gentoo_overlay_mirrors(repo_name):
    """Get the gentoo overlay repos that match repo.id
    """
    gentoo_overlays_url = 'https://api.gentoo.org/overlays/repositories.xml'
    res = get_url(gentoo_overlays_url)
    if not res:
        return
    mirrors = []
    try:
        tree = ElementTree.parse(BytesIO(res.content))
        root = tree.getroot()
        for child in root:
            if child.tag == 'repo':
                found = False
                for element in child:
                    if element.tag == 'name' and element.text == repo_name:
                        found = True
                    if found and element.tag == 'source':
                        if element.text.startswith('http'):
                            mirrors.append(element.text)
    except ElementTree.ParseError as e:
        error_message.send(sender=None, text=f'Error parsing {gentoo_overlays_url}: {e}')
    return mirrors


def get_gentoo_mirror_urls():
    """ Use the Gentoo API to find http(s) mirrors
    """
    gentoo_distfiles_url = 'https://api.gentoo.org/mirrors/distfiles.xml'
    res = get_url(gentoo_distfiles_url)
    if not res:
        return
    mirrors = {}
    try:
        tree = ElementTree.parse(BytesIO(res.content))
        root = tree.getroot()
        for child in root:
            if child.tag == 'mirrorgroup':
                for k, v in child.attrib.items():
                    if k == 'region':
                        region = v
                    elif k == 'country':
                        country = v
                for mirror in child:
                    for element in mirror:
                        if element.tag == 'name':
                            name = element.text
                            mirrors[name] = {}
                            mirrors[name]['region'] = region
                            mirrors[name]['country'] = country
                            mirrors[name]['urls'] = []
                        elif element.tag == 'uri':
                            if element.get('protocol') == 'http':
                                mirrors[name]['urls'].append(element.text)
    except ElementTree.ParseError as e:
        error_message.send(sender=None, text=f'Error parsing {gentoo_distfiles_url}: {e}')
    mirror_urls = []
    # for now, ignore region data and choose MAX_MIRRORS mirrors at random
    for _, v in mirrors.items():
        for url in v['urls']:
            mirror_urls.append(url.rstrip('/') + '/snapshots/gentoo-latest.tar.xz')
    return mirror_urls


def extract_gentoo_ebuilds(data):
    """ Extract ebuilds from a Gentoo tarball
    """
    extracted_ebuilds = {}
    with tarfile.open(fileobj=BytesIO(data), mode='r') as tar:
        for member in tar.getmembers():
            if member.isfile() and member.name.endswith('ebuild') and not member.name.endswith('skel.ebuild'):
                file_content = tar.extractfile(member).read()
                full_path = Path(member.name)
                ebuild_path = Path(*full_path.parts[1:])
                extracted_ebuilds[str(ebuild_path)] = file_content
    return extracted_ebuilds


def extract_gentoo_overlay_ebuilds(t):
    """ Extract ebuilds from a Gentoo overlay tarball
    """
    extracted_ebuilds = {}
    for root, _, files in os.walk(t):
        for name in files:
            if fnmatch(name, '*.ebuild'):
                package_name = root.replace(t + '/', '')
                if len(package_name.split('/')) > 2:
                    continue
                with open(os.path.join(root, name), 'rb') as f:
                    content = f.read()
                extracted_ebuilds[f'{package_name}/{name}'] = content
    return extracted_ebuilds


def extract_gentoo_packages(mirror, data):
    """ Extract packages from a Gentoo mirror
    """
    extracted_ebuilds = extract_gentoo_ebuilds(data)
    return extract_gentoo_packages_from_ebuilds(extracted_ebuilds)


def extract_gentoo_packages_from_ebuilds(extracted_ebuilds):
    """ Extract packages from ebuilds
    """
    if not extracted_ebuilds:
        return

    packages = set()
    elen = len(extracted_ebuilds)
    pbar_start.send(sender=None, ptext=f'Processing {elen} ebuilds', plen=elen)
    for i, (path, content) in enumerate(extracted_ebuilds.items()):
        pbar_update.send(sender=None, index=i + 1)
        components = path.split(os.sep)
        category = components[0]
        name = components[1]
        evr = components[2].replace(f'{name}-', '').replace('.ebuild', '')
        epoch, version, release = find_evr(evr)
        arches = get_gentoo_ebuild_keywords(content)
        for arch in arches:
            package = PackageString(
                name=name.lower(),
                epoch=epoch,
                version=version,
                release=release,
                arch=arch,
                packagetype='G',
                category=category,
            )
            packages.add(package)
    plen = len(packages)
    info_message.send(sender=None, text=f'Extracted {plen} Packages', plen=plen)
    return packages


def extract_gentoo_overlay_packages(mirror):
    """ Extract packages from gentoo overlay repo
    """
    t = tempfile.mkdtemp()
    info_message.send(sender=None, text=f'Extracting Gentoo packages from {mirror.url}')
    git.Repo.clone_from(mirror.url, t, depth=1)
    packages = set()
    extracted_ebuilds = extract_gentoo_overlay_ebuilds(t)
    shutil.rmtree(t)
    packages = extract_gentoo_packages_from_ebuilds(extracted_ebuilds)
    return packages


def refresh_gentoo_repo(repo):
    """ Refresh a Gentoo repo
    """
    if repo.repo_id == 'gentoo':
        refresh_gentoo_main_repo(repo)
    else:
        refresh_gentoo_overlay_repo(repo)
