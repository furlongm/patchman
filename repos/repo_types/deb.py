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

import re

from debian.deb822 import Packages
from debian.debian_support import Version

from packages.models import PackageString
from patchman.signals import pbar_start, pbar_update
from repos.utils import (
    fetch_mirror_data, find_mirror_url, update_mirror_packages,
)
from util import Checksum, extract, get_checksum, get_datetime_now
from util.logging import error_message, info_message, warning_message


def extract_deb_packages(data, url):
    """ Extract package metadata from debian Packages file
    """
    try:
        extracted = extract(data, url).decode('utf-8')
    except UnicodeDecodeError as e:
        error_message(text=f'Skipping {url} : {e}')
        return
    package_re = re.compile('^Package: ', re.M)
    plen = len(package_re.findall(extracted))
    packages = set()

    if plen > 0:
        pbar_start.send(sender=None, ptext=f'Extracting {plen} Packages', plen=plen)
        for i, stanza in enumerate(Packages.iter_paragraphs(extracted)):
            # https://github.com/furlongm/patchman/issues/55
            if 'version' not in stanza:
                continue
            fullversion = Version(stanza['version'])
            arch = stanza['architecture']
            name = stanza['package']
            epoch = fullversion._BaseVersion__epoch
            if epoch is None:
                epoch = ''
            version = fullversion._BaseVersion__upstream_version
            release = fullversion._BaseVersion__debian_revision
            if release is None:
                release = ''
            pbar_update.send(sender=None, index=i + 1)
            package = PackageString(name=name,
                                    epoch=epoch,
                                    version=version,
                                    release=release,
                                    arch=arch,
                                    packagetype='D')
            packages.add(package)
    else:
        info_message(text='No packages found in repo')
    return packages


def refresh_deb_repo(repo):
    """ Refresh a debian repo.
        Checks for the Packages* files to determine what the mirror urls
        are and then fetches and extracts packages from those files.
    """

    formats = [
        'Packages.xz',
        'Packages.bz2',
        'Packages.gz',
        'Packages',
    ]

    ts = get_datetime_now()
    enabled_mirrors = repo.mirror_set.filter(refresh=True, enabled=True)
    for mirror in enabled_mirrors:
        res = find_mirror_url(mirror.url, formats)
        if not res:
            continue
        mirror_url = res.url
        text = f'Found deb Repo - {mirror_url}'
        info_message(text=text)

        package_data = fetch_mirror_data(
            mirror=mirror,
            url=mirror_url,
            text='Fetching Debian Repo data')
        if not package_data:
            continue

        computed_checksum = get_checksum(package_data, Checksum.sha1)
        if mirror.packages_checksum == computed_checksum:
            text = 'Mirror checksum has not changed, not refreshing Package metadata'
            warning_message(text=text)
            continue
        else:
            mirror.packages_checksum = computed_checksum

        packages = extract_deb_packages(package_data, mirror_url)
        if not packages:
            mirror.fail()
            continue

        update_mirror_packages(mirror, packages)
        packages.clear()
        mirror.timestamp = ts
        mirror.save()
