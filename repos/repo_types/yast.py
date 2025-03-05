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

from packages.models import PackageString
from patchman.signals import pbar_start, pbar_update, info_message
from repos.utils import fetch_mirror_data, update_mirror_packages
from util import extract


def refresh_yast_repo(mirror, data):
    """ Refresh package metadata for a yast-style rpm mirror
        and add the packages to the mirror
    """
    package_dir = re.findall('DESCRDIR *(.*)', data.decode('utf-8'))[0]
    package_url = f'{mirror.url}/{package_dir}/packages.gz'

    package_data = fetch_mirror_data(
        mirror=mirror,
        url=package_url,
        text='Downloading yast Repo data')
    if not package_data:
        return

    mirror.packages_checksum = 'yast'
    packages = extract_yast_packages(package_data)
    if packages:
        update_mirror_packages(mirror, packages)
        packages.clear()


def extract_yast_packages(data):
    """ Extract package metadata from yast metadata file
    """
    extracted = extract(data, 'gz').decode('utf-8')
    pkgs = re.findall('=Pkg: (.*)', extracted)
    plen = len(pkgs)
    packages = set()

    if plen > 0:
        pbar_start.send(sender=None, ptext=f'Extracting {plen} Packages', plen=plen)

        for i, pkg in enumerate(pkgs):
            pbar_update.send(sender=None, index=i + 1)
            name, version, release, arch = pkg.split()
            package = PackageString(name=name.lower(),
                                    epoch='',
                                    version=version,
                                    release=release,
                                    arch=arch,
                                    packagetype='R')
            packages.add(package)
    else:
        info_message.send(sender=None, text='No packages found in repo')
    return packages
