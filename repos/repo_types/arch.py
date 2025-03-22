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

import tarfile
from io import BytesIO

from packages.models import PackageString
from patchman.signals import info_message, warning_message, pbar_start, pbar_update
from repos.utils import get_max_mirrors, fetch_mirror_data, find_mirror_url, update_mirror_packages
from util import get_datetime_now, get_checksum, Checksum


def refresh_arch_repo(repo):
    """ Refresh all mirrors of an arch linux repo
    """
    max_mirrors = get_max_mirrors()
    fname = f'{repo.arch}/{repo.repo_id}.db'
    ts = get_datetime_now()

    enabled_mirrors = repo.mirror_set.filter(refresh=True, enabled=True)
    for i, mirror in enumerate(enabled_mirrors):
        if i >= max_mirrors:
            text = f'{max_mirrors} Mirrors already refreshed (max={max_mirrors}), skipping further refreshes'
            warning_message.send(sender=None, text=text)
            break

        res = find_mirror_url(mirror.url, [fname])
        if not res:
            continue
        mirror_url = res.url
        text = f'Found Arch Repo - {mirror_url}'
        info_message.send(sender=None, text=text)

        package_data = fetch_mirror_data(
            mirror=mirror,
            url=mirror_url,
            text='Fetching Repo data')
        if not package_data:
            continue

        computed_checksum = get_checksum(package_data, Checksum.sha1)
        if mirror.packages_checksum == computed_checksum:
            text = 'Mirror checksum has not changed, not refreshing Package metadata'
            warning_message.send(sender=None, text=text)
            continue
        else:
            mirror.packages_checksum = computed_checksum

        packages = extract_arch_packages(package_data)
        update_mirror_packages(mirror, packages)
        packages.clear()
        mirror.timestamp = ts
        mirror.save()


def extract_arch_packages(data):
    """ Extract package metadata from an arch linux tarfile
    """
    from packages.utils import find_evr
    bio = BytesIO(data)
    tf = tarfile.open(fileobj=bio, mode='r:*')
    packages = set()
    plen = len(tf.getnames())
    if plen > 0:
        pbar_start.send(sender=None, ptext=f'Extracting {plen} Packages', plen=plen)
        for i, tarinfo in enumerate(tf):
            pbar_update.send(sender=None, index=i + 1)
            if tarinfo.isfile():
                name_sec = ver_sec = arch_sec = False
                t = tf.extractfile(tarinfo).read()
                for line in t.decode('utf-8').splitlines():
                    if line.startswith('%NAME%'):
                        name_sec = True
                        continue
                    if name_sec:
                        name_sec = False
                        name = line
                        continue
                    if line.startswith('%VERSION%'):
                        ver_sec = True
                        continue
                    if ver_sec:
                        ver_sec = False
                        epoch, version, release = find_evr(line)
                        continue
                    if line.startswith('%ARCH%'):
                        arch_sec = True
                        continue
                    if arch_sec:
                        arch_sec = False
                        arch = line
                        continue
                package = PackageString(name=name.lower(),
                                        epoch=epoch,
                                        version=version,
                                        release=release,
                                        arch=arch,
                                        packagetype='A')
                packages.add(package)
    else:
        info_message.send(sender=None, text='No Packages found in Repo')
    return packages
