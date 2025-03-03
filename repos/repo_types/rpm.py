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

from django.db.models import Q

from patchman.signals import info_message, warning_message
from repos.repo_types.yast import refresh_yast_repo
from repos.repo_types.yum import refresh_yum_repo
from repos.utils import check_for_metalinks, check_for_mirrorlists, find_mirror_url, get_max_mirrors, fetch_mirror_data
from util import get_datetime_now


def refresh_repo_errata(repo):
    refresh_rpm_repo_mirrors(repo, errata_only=True)


def refresh_rpm_repo(repo):
    """ Refresh an rpm repo (yum or yast)
        Checks if the repo url is a mirrorlist or metalink,
        and extracts mirrors if so, then refreshes the mirrors
    """
    check_for_mirrorlists(repo)
    check_for_metalinks(repo)
    refresh_rpm_repo_mirrors(repo)


def max_mirrors_refreshed(repo, checksum, ts):
    """ Only refresh X mirrors, where X = max_mirrors
    """
    if checksum is None:
        return False
    max_mirrors = get_max_mirrors()
    mirrors_q = Q(mirrorlist=False, refresh=True, enabled=True, timestamp=ts, packages_checksum=checksum)
    have_checksum_and_ts = repo.mirror_set.filter(mirrors_q).count()
    if have_checksum_and_ts >= max_mirrors:
        text = f'{max_mirrors} Mirrors already have this checksum and timestamp, skipping further refreshes'
        warning_message.send(sender=None, text=text)
        return True
    return False


def refresh_rpm_repo_mirrors(repo, errata_only=False):
    """ Checks a number of common yum repo formats to determine
        which type of repo it is, then refreshes the mirrors
    """
    formats = [
        'repodata/repomd.xml.xz',
        'repodata/repomd.xml.bz2',
        'repodata/repomd.xml.gz',
        'repodata/repomd.xml',
        'suse/repodata/repomd.xml.xz',
        'suse/repodata/repomd.xml.bz2',
        'suse/repodata/repomd.xml.gz',
        'suse/repodata/repomd.xml',
        'content',
    ]
    ts = get_datetime_now()
    enabled_mirrors = repo.mirror_set.filter(mirrorlist=False, refresh=True, enabled=True)
    for i, mirror in enumerate(enabled_mirrors):
        res = find_mirror_url(mirror.url, formats)
        if not res:
            mirror.fail()
            continue
        mirror_url = res.url

        repo_data = fetch_mirror_data(
            mirror=mirror,
            url=mirror_url,
            text='Downloading Repo data')
        if not repo_data:
            continue

        if mirror_url.endswith('content'):
            text = f'Found yast rpm Repo - {mirror_url}'
            info_message.send(sender=None, text=text)
            refresh_yast_repo(mirror, repo_data)
        else:
            text = f'Found yum rpm Repo - {mirror_url}'
            info_message.send(sender=None, text=text)
            refresh_yum_repo(mirror, repo_data, mirror_url, errata_only)
        if mirror.last_access_ok:
            mirror.timestamp = ts
            mirror.save()
            checksum = mirror.packages_checksum
            if max_mirrors_refreshed(repo, checksum, ts):
                break
