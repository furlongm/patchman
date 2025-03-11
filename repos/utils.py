# Copyright 2012 VPAC, http://www.vpac.org
# Copyright 2013-2025 Marcus Furlong <furlongm@gmail.com>
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
from io import BytesIO
from defusedxml import ElementTree
from tenacity import RetryError

from django.db import IntegrityError
from django.db.models import Q

from packages.models import Package
from packages.utils import convert_package_to_packagestring, convert_packagestring_to_package
from util import get_url, fetch_content, response_is_valid, extract, get_checksum, Checksum, get_setting_of_type
from patchman.signals import info_message, warning_message, error_message, debug_message, pbar_start, pbar_update


def get_or_create_repo(r_name, r_arch, r_type, r_id=None):
    """ Get or create a Repository object and returns the object.
        Returns None if it cannot get or create the object.
    """
    from repos.models import Repository
    try:
        repository, c = Repository.objects.get_or_create(name=r_name, arch=r_arch, repotype=r_type)
    except IntegrityError:
        repository = Repository.objects.get(name=r_name, arch=r_arch, repotype=r_type)
    if repository:
        if r_id:
            repository.repo_id = r_id
            repository.save()
        return repository


def update_mirror_packages(mirror, packages):
    """ Updates the packages contained on a mirror, and
        removes obsolete packages.
    """
    from repos.models import MirrorPackage  # noqa

    old = set()
    mirror_packages = mirror.packages.all()
    plen = mirror_packages.count()
    pbar_start.send(sender=None, ptext=f'Fetching {plen} existing Packages', plen=plen)
    for i, package in enumerate(mirror_packages):
        pbar_update.send(sender=None, index=i + 1)
        strpackage = convert_package_to_packagestring(package)
        old.add(strpackage)

    removals = old.difference(packages)
    rlen = len(removals)
    pbar_start.send(sender=None, ptext=f'Removing {rlen} obsolete Packages', plen=rlen)
    for i, strpackage in enumerate(removals):
        pbar_update.send(sender=None, index=i + 1)
        package = convert_packagestring_to_package(strpackage)
        MirrorPackage.objects.filter(mirror=mirror, package=package).delete()

    new = packages.difference(old)
    nlen = len(new)
    pbar_start.send(sender=None, ptext=f'Adding {nlen} new Packages', plen=nlen)
    for i, strpackage in enumerate(new):
        pbar_update.send(sender=None, index=i + 1)
        try:
            package = convert_packagestring_to_package(strpackage)
            mirror_package, c = MirrorPackage.objects.get_or_create(mirror=mirror, package=package)
        except Package.MultipleObjectsReturned:
            error_message.send(sender=None, text=f'Duplicate Package found in {mirror}: {strpackage}')


def find_mirror_url(stored_mirror_url, formats):
    """ Find the actual URL of the mirror by trying predefined paths
    """
    for fmt in formats:
        mirror_url = stored_mirror_url
        for f in formats:
            if mirror_url.endswith(f):
                mirror_url = mirror_url[:-len(f)]
        mirror_url = f"{mirror_url.rstrip('/')}/{fmt}"
        debug_message.send(sender=None, text=f'Checking for Mirror at {mirror_url}')
        try:
            res = get_url(mirror_url)
        except RetryError:
            continue
        if res is not None and res.ok:
            return res


def is_metalink(url):
    """ Checks if a given url is a metalink url
    """
    return 'metalink?' in url.lower()


def get_metalink_urls(url):
    """  Parses a metalink and returns a list of mirrors
    """
    try:
        res = get_url(url)
    except RetryError:
        return
    if not response_is_valid(res):
        return
    if not res.headers.get('content-type') == 'application/metalink+xml':
        return
    metalink_urls = []
    data = fetch_content(res, 'Fetching metalink data')
    extracted = extract(data, url)
    ns = 'http://www.metalinker.org/'
    try:
        tree = ElementTree.parse(BytesIO(extracted))
        root = tree.getroot()
        for child in root:
            if child.tag == f'{{{ns}}}files':
                for grandchild in child:
                    if grandchild.tag == f'{{{ns}}}file':
                        for greatgrandchild in grandchild:
                            if greatgrandchild.tag == f'{{{ns}}}resources':
                                for greatgreatgrandchild in greatgrandchild:
                                    if greatgreatgrandchild.tag == f'{{{ns}}}url':
                                        if greatgreatgrandchild.attrib.get('protocol') in ['https', 'http']:
                                            metalink_urls.append(greatgreatgrandchild.text)
    except ElementTree.ParseError as e:
        error_message.send(sender=None, text=f'Error parsing metalink {url}: {e}')
    return metalink_urls


def get_mirrorlist_urls(url):
    """ Checks if a given url returns a mirrorlist by checking if it contains
        a list of urls. Returns a list of mirrors if it is a mirrorlist.
    """
    try:
        res = get_url(url)
    except RetryError:
        return
    if response_is_valid(res):
        try:
            data = fetch_content(res, 'Fetching Repo data')
            if data is None:
                return
            mirror_urls = re.findall(r'^http[s]*://.*$|^ftp://.*$', data.decode('utf-8'), re.MULTILINE)
            if mirror_urls:
                debug_message.send(sender=None, text=f'Found mirrorlist: {url}')
                return mirror_urls
            else:
                debug_message.send(sender=None, text=f'Not a mirrorlist: {url}')
        except Exception as e:
            error_message.send(sender=None, text=f'Error attempting to parse a mirrorlist: {e} {url}')


def add_mirrors_from_urls(repo, mirror_urls):
    """ Creates mirrors from a list of mirror urls
    """
    max_mirrors = get_max_mirrors()
    for mirror_url in mirror_urls:
        mirror_url = mirror_url.replace('$ARCH', repo.arch.name)
        mirror_url = mirror_url.replace('$basearch', repo.arch.name)
        mirror_url = mirror_url.rstrip('/')
        q = Q(mirrorlist=False, refresh=True, enabled=True)
        existing = repo.mirror_set.filter(q).count()
        if existing >= max_mirrors:
            text = f'{existing} Mirrors already exist (max={max_mirrors}), not adding more'
            warning_message.send(sender=None, text=text)
            break
        from repos.models import Mirror
        # FIXME: maybe we should store the mirrorlist url with full path to repomd.xml?
        # that is what metalink urls return now
        m, c = Mirror.objects.get_or_create(repo=repo, url=mirror_url.rstrip('/').replace('repodata/repomd.xml', ''))
        if c:
            text = f'Added Mirror - {mirror_url}'
            info_message.send(sender=None, text=text)


def check_for_mirrorlists(repo):
    """ Check if any of the mirrors are actually mirrorlists.
        Creates MAX_MIRRORS mirrors from list if so.
    """
    for mirror in repo.mirror_set.all():
        mirror_urls = get_mirrorlist_urls(mirror.url)
        if mirror_urls:
            mirror.mirrorlist = True
            mirror.last_access_ok = True
            mirror.save()
            info_message.send(sender=None, text=f'Found mirrorlist - {mirror.url}')
            add_mirrors_from_urls(repo, mirror_urls)


def check_for_metalinks(repo):
    """ Checks a set of mirrors for metalinks and creates
        MAX_MIRRORS mirrors if so.
    """
    for mirror in repo.mirror_set.all():
        if is_metalink(mirror.url):
            mirror_urls = get_metalink_urls(mirror.url)
        else:
            continue
        if mirror_urls:
            mirror.mirrorlist = True
            mirror.last_access_ok = True
            mirror.save()
            info_message.send(sender=None, text=f'Found metalink - {mirror.url}')
            add_mirrors_from_urls(repo, mirror_urls)


def fetch_mirror_data(mirror, url, text, checksum=None, checksum_type=None, metadata_type=None):
    if not url:
        mirror.fail()
        return

    try:
        res = get_url(url)
    except RetryError:
        mirror.fail()
        return

    if not response_is_valid(res):
        mirror.fail()
        return
    mirror.last_access_ok = True
    mirror.save()

    data = fetch_content(res, text)
    if not data:
        return

    if checksum and checksum_type and metadata_type:
        computed_checksum = get_checksum(data, Checksum[checksum_type])
        if not mirror_checksum_is_valid(computed_checksum, checksum, mirror, metadata_type):
            mirror.fail()
            return
    return data


def mirror_checksum_is_valid(computed, provided, mirror, metadata_type):
    """ Compares the computed checksum and the provided checksum.
        Returns True if both match.
    """
    if not computed or computed != provided:
        text = f'Checksum failed for mirror {mirror.id}, not refreshing {metadata_type} metadata'
        error_message.send(sender=None, text=text)
        text = f'Found checksum:    {computed}\nExpected checksum: {provided}'
        error_message.send(sender=None, text=text)
        mirror.last_access_ok = False
        mirror.fail()
        return False
    else:
        return True


def find_best_repo(package, hostrepos):
    """ Given a package and a set of HostRepos, determine the best
        repo. Returns the best repo.
    """
    best_repo = None
    package_repos = hostrepos.filter(repo__mirror__packages=package).distinct()

    if package_repos:
        best_repo = package_repos[0]
    if package_repos.count() > 1:
        for hostrepo in package_repos:
            if hostrepo.repo.security:
                best_repo = hostrepo
            else:
                if hostrepo.priority > best_repo.priority:
                    best_repo = hostrepo
    return best_repo


def get_max_mirrors():
    """ Find the max number of mirrors for refresh
    """
    max_mirrors = get_setting_of_type(
        setting_name='MAX_MIRRORS',
        setting_type=int,
        default=3,
    )
    return max_mirrors


def clean_repos():
    """ Remove repositories that contain no mirrors
    """
    from repos.models import Repository
    repos = Repository.objects.filter(mirror__isnull=True)
    rlen = repos.count()
    if rlen == 0:
        info_message.send(sender=None, text='No Repositories with zero Mirrors found.')
    else:
        info_message.send(sender=None, text=f'Removing {rlen} empty Repositories.')
        repos.delete()


def remove_mirror_trailing_slashes():
    """ Remove trailing slashes from mirrors, delete duplicates
    """
    from repos.models import Mirror
    mirrors = Mirror.objects.filter(url__endswith='/')
    mlen = mirrors.count()
    if mlen == 0:
        info_message.send(sender=None, text='No Mirrors with trailing slashes found.')
    else:
        info_message.send(sender=None, text=f'Removing trailing slashes from {mlen} Mirrors.')
        for mirror in mirrors:
            mirror.url = mirror.url.rstrip('/')
            try:
                mirror.save()
            except IntegrityError:
                warning_message.send(sender=None, text=f'Deleting duplicate Mirror {mirror.id}: {mirror.url}')
                mirror.delete()
