# Copyright 2012 VPAC, http://www.vpac.org
# Copyright 2013-2016 Marcus Furlong <furlongm@gmail.com>
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

import os
import re
try:
    import lzma
except ImportError:
    try:
        from backports import lzma
    except ImportError:
        lzma = None
from datetime import datetime
from hashlib import sha1, sha256
from io import BytesIO
from lxml import etree
from debian.debian_support import Version
from debian.deb822 import Sources

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'patchman.settings')
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils.six import text_type

from patchman.packages.models import Package, PackageName, PackageString
from patchman.arch.models import PackageArchitecture
from patchman.util import get_url, download_url, response_is_valid, extract
from patchman.signals import progress_info_s, progress_update_s, \
    info_message, warning_message, error_message, debug_message


def update_mirror_packages(mirror, packages):
    """ Updates the packages contained on a mirror, and
        removes obsolete packages.
    """
    new = set()
    old = set()
    removals = set()

    mirror_packages = mirror.packages.all()
    mlen = mirror_packages.count()

    ptext = 'Obtaining stored packages: '
    progress_info_s.send(sender=None, ptext=ptext, plen=mlen)
    for i, package in enumerate(mirror_packages):
        progress_update_s.send(sender=None, index=i + 1)
        name = str(package.name)
        arch = str(package.arch)
        strpackage = PackageString(name=name,
                                   epoch=package.epoch,
                                   version=package.version,
                                   release=package.release,
                                   arch=arch,
                                   packagetype=package.packagetype)
        old.add(strpackage)

    new = packages.difference(old)
    removals = old.difference(packages)

    nlen = len(new)
    rlen = len(removals)

    ptext = 'Removing {0!s} obsolete packages:'.format(rlen)
    progress_info_s.send(sender=None, ptext=ptext, plen=rlen)
    for i, package in enumerate(removals):
        progress_update_s.send(sender=None, index=i + 1)
        package_id = PackageName.objects.get(name=package.name)
        epoch = package.epoch
        version = package.version
        release = package.release
        arch = PackageArchitecture.objects.get(name=package.arch)
        packagetype = package.packagetype
        p = Package.objects.get(name=package_id,
                                epoch=epoch,
                                version=version,
                                arch=arch,
                                release=release,
                                packagetype=packagetype)
        from patchman.repos.models import MirrorPackage
        with transaction.atomic():
            MirrorPackage.objects.get(mirror=mirror, package=p).delete()

    ptext = 'Adding {0!s} new packages:'.format(nlen)
    progress_info_s.send(sender=None, ptext=ptext, plen=nlen)
    for i, package in enumerate(new):
        progress_update_s.send(sender=None, index=i + 1)

        package_names = PackageName.objects.all()
        with transaction.atomic():
            package_id, c = package_names.get_or_create(name=package.name)

        epoch = package.epoch
        version = package.version
        release = package.release
        packagetype = package.packagetype

        package_arches = PackageArchitecture.objects.all()
        with transaction.atomic():
            arch, c = package_arches.get_or_create(name=package.arch)

        all_packages = Package.objects.all()
        with transaction.atomic():
            p, c = all_packages.get_or_create(name=package_id,
                                              epoch=epoch,
                                              version=version,
                                              arch=arch,
                                              release=release,
                                              packagetype=packagetype)
        # This fixes a subtle bug where a stored package name with uppercase
        # letters will not match until it is lowercased.
        if package_id.name != package.name:
            package_id.name = package.name
            with transaction.atomic():
                package_id.save()
        from patchman.repos.models import MirrorPackage
        with transaction.atomic():
            MirrorPackage.objects.create(mirror=mirror, package=p)


def get_primary_url(mirror_url, data):

    if isinstance(data, text_type):
        if data.startswith('Bad repo - not in list') or \
                data.startswith('Invalid repo'):
            return None, None, None
    ns = 'http://linux.duke.edu/metadata/repo'
    try:
        context = etree.parse(BytesIO(data), etree.XMLParser())
    except etree.XMLSyntaxError:
        context = etree.parse(BytesIO(extract(data, 'gz')), etree.XMLParser())
    location = context.xpath("//ns:data[@type='primary']/ns:location/@href",
                             namespaces={'ns': ns})[0]
    checksum = context.xpath("//ns:data[@type='primary']/ns:checksum",
                             namespaces={'ns': ns})[0].text
    csum_type = context.xpath("//ns:data[@type='primary']/ns:checksum/@type",
                              namespaces={'ns': ns})[0]
    primary_url = str(mirror_url.rsplit('/', 2)[0]) + '/' + location
    return primary_url, checksum, csum_type


def get_sha1(data):
    return sha1(data).hexdigest()


def get_sha256(data):
    return sha256(data).hexdigest()


def get_sha(checksum_type, data):
    """ Returns the checksum of the data. Returns None otherwise.
    """
    if checksum_type == 'sha':
        sha = get_sha1(data)
    elif checksum_type == 'sha256':
        sha = get_sha256(data)
    else:
        text = 'Unknown checksum type: {0!s}'.format(checksum_type)
        error_message.send(sender=None, text=text)
    return sha


def find_mirror_url(stored_mirror_url, formats):
    """ Find the actual URL of the mirror by trying predefined paths
    """

    for fmt in formats:
        mirror_url = stored_mirror_url
        for f in formats:
            if mirror_url.endswith(f):
                mirror_url = mirror_url[:-len(f)]
        mirror_url = mirror_url.rstrip('/') + '/' + fmt
        debug_message.send(sender=None,
                           text='Checking {0!s}'.format(mirror_url))
        res = get_url(mirror_url)
        if res is not None and res.ok:
            return res


def mirrorlist_check(mirror_url):
    """ Checks if a given url returns a mirrorlist.
        Does this by checking if it is of type text/plain
        and contains a list of urls
    """

    res = get_url(mirror_url)
    if response_is_valid(res):
        if 'content-type' in res.headers and \
           'text/plain' in res.headers['content-type']:
            data = download_url(res, 'Downloading repo info:')
            if data is None:
                return
            mirror_urls = re.findall(b'^http://.*$|^ftp://.*$',
                                     data, re.MULTILINE)
            if mirror_urls:
                return mirror_urls
    return


def mirrorlists_check(repo):
    """ Check if any of the mirrors are actually mirrorlists
    """

    for mirror in repo.mirror_set.all():
        mirror_urls = mirrorlist_check(mirror.url)
        if mirror_urls:
            mirror.mirrorlist = True
            mirror.last_access_ok = True
            mirror.save()
            text = 'Found mirrorlist - {0!s}'.format(mirror.url)
            info_message.send(sender=None, text=text)
            for mirror_url in mirror_urls:
                mirror_url = mirror_url.decode('ascii')
                mirror_url = mirror_url.replace('$ARCH', repo.arch.name)
                mirror_url = mirror_url.replace('$basearch', repo.arch.name)
                if hasattr(settings, 'MAX_MIRRORS') and \
                        isinstance(settings.MAX_MIRRORS, int):
                    max_mirrors = settings.MAX_MIRRORS
                    # only add X mirrors, where X = max_mirrors
                    q = Q(mirrorlist=False, refresh=True)
                    existing = mirror.repo.mirror_set.filter(q).count()
                    if existing >= max_mirrors:
                        text = '{0!s} mirrors already '.format(max_mirrors)
                        text += 'exist, not adding {0!s}'.format(mirror_url)
                        warning_message.send(sender=None, text=text)
                        continue
                from patchman.repos.models import Mirror
                m, c = Mirror.objects.get_or_create(repo=repo, url=mirror_url)
                if c:
                    text = 'Added mirror - {0!s}'.format(mirror_url)
                    info_message.send(sender=None, text=text)


def extract_yum_packages(data, url):
    """ Extract package metadata from a yum primary.xml file
    """

    extracted = extract(data, url)
    ns = 'http://linux.duke.edu/metadata/common'
    context = etree.iterparse(BytesIO(extracted),
                              tag='{{{0!s}}}metadata'.format(ns))
    plen = int(next(context)[1].get('packages'))
    context = etree.iterparse(BytesIO(extracted),
                              tag='{{{0!s}}}package'.format(ns))
    packages = set()

    if plen > 0:
        ptext = 'Extracting packages: '
        progress_info_s.send(sender=None, ptext=ptext, plen=plen)

        for i, data in enumerate(context):
            elem = data[1]
            progress_update_s.send(sender=None, index=i + 1)
            name = elem.xpath('//ns:name',
                              namespaces={'ns': ns})[0].text.lower()
            arch = elem.xpath('//ns:arch',
                              namespaces={'ns': ns})[0].text
            fullversion = elem.xpath('//ns:version',
                                     namespaces={'ns': ns})[0]
            epoch = fullversion.get('epoch')
            version = fullversion.get('ver')
            release = fullversion.get('rel')
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]

            if name != '' and version != '' and arch != '':
                if epoch == '0':
                    epoch = ''
                package = PackageString(name=name,
                                        epoch=epoch,
                                        version=version,
                                        release=release,
                                        arch=arch,
                                        packagetype='R')
                packages.add(package)
    else:
        info_message.send(sender=None, text='No packages found in repo')
    return packages


def extract_deb_packages(data, url):
    """ Extract package metadata from debian Packages file
    """

    extracted = extract(data, url)
    package_re = re.compile(b'^Package: ', re.M)
    plen = len(package_re.findall(extracted))
    packages = set()

    if plen > 0:
        ptext = 'Extracting packages: '
        progress_info_s.send(sender=None, ptext=ptext, plen=plen)

        bio = BytesIO(extracted)
        for i, stanza in enumerate(Sources.iter_paragraphs(bio)):
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
            progress_update_s.send(sender=None, index=i + 1)
            package = PackageString(name=name,
                                    epoch=epoch,
                                    version=version,
                                    release=release,
                                    arch=arch,
                                    packagetype='D')
            packages.add(package)
    else:
        info_message.send(sender=None, text='No packages found in repo')
    return packages


def extract_yast_packages(data):
    """ Extract package metadata from yast metadata file
    """

    extracted = extract(data, 'gz')
    pkgs = re.findall(b'=Pkg: (.*)', extracted)
    plen = len(pkgs)
    packages = set()

    if plen > 0:
        ptext = 'Extracting packages: '
        progress_info_s.send(sender=None, ptext=ptext, plen=plen)

        for i, pkg in enumerate(pkgs):
            progress_update_s.send(sender=None, index=i + 1)
            name, version, release, arch = str(pkg).split()
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


def refresh_yum_repo(mirror, data, mirror_url, ts):
    """ Refresh package metadata for a yum-style rpm mirror
        and add the packages to the mirror
    """

    primary_url, checksum, checksum_type = get_primary_url(mirror_url, data)

    if not primary_url:
        mirror.fail()
        return

    res = get_url(primary_url)
    mirror.last_access_ok = response_is_valid(res)

    if not mirror.last_access_ok:
        mirror.fail()
        return

    data = download_url(res, 'Downloading repo info (2/2):')
    if data is None:
        mirror.fail()
        return

    sha = get_sha(checksum_type, data)
    if sha is None:
        mirror.fail()
        return

    if not checksum_is_valid(sha, checksum, mirror):
        mirror.fail()
        return

    if mirror.file_checksum == checksum:
        text = 'Mirror checksum has not changed, '
        text += 'not refreshing package metadata'
        warning_message.send(sender=None, text=text)
        return

    mirror.file_checksum = checksum

    if hasattr(settings, 'MAX_MIRRORS') and \
            isinstance(settings.MAX_MIRRORS, int):
        max_mirrors = settings.MAX_MIRRORS
        # only refresh X mirrors, where X = max_mirrors
        checksum_q = Q(mirrorlist=False, refresh=True, timestamp=ts,
                       file_checksum=checksum)
        have_checksum = mirror.repo.mirror_set.filter(checksum_q).count()
        if have_checksum >= max_mirrors:
            text = '{0!s} mirrors already have this '.format(max_mirrors)
            text += 'checksum, ignoring refresh to save time'
            info_message.send(sender=None, text=text)
        else:
            packages = extract_yum_packages(data, primary_url)
            if packages:
                update_mirror_packages(mirror, packages)


def checksum_is_valid(sha, checksum, mirror):
    """ Compares the computed checksum and the provided checksum. Returns True
        if both match.
    """

    if sha == checksum:
        return True
    else:
        text = 'Checksum failed for mirror {0!s}'.format(mirror.id)
        text += ', not refreshing package metadata'
        error_message.send(sender=None, text=text)
        text = 'Found sha = {0!s}\nExpected  = {1!s}'.format(sha, checksum)
        error_message.send(sender=None, text=text)
        mirror.last_access_ok = False
        return False


def refresh_yast_repo(mirror, data):
    """ Refresh package metadata for a yast-style rpm mirror
        and add the packages to the mirror
    """

    package_dir = re.findall(b'DESCRDIR *(.*)', data)[0].decode('ascii')
    package_url = '{0!s}/{1!s}/packages.gz'.format(mirror.url, package_dir)
    res = get_url(package_url)
    mirror.last_access_ok = response_is_valid(res)
    if mirror.last_access_ok:
        data = download_url(res, 'Downloading repo info (2/2):')
        if data is None:
            mirror.fail()
            return
        mirror.file_checksum = 'yast'
        packages = extract_yast_packages(data)
        if packages:
            update_mirror_packages(mirror, packages)
    else:
        mirror.fail()


def refresh_rpm_repo(repo):
    """ Refresh an rpm repo.
        Checks if the repo url is a mirrorlist, and extracts mirrors if so.
        If not, checks a number of common rpm repo formats to determine
        which type of repo it is, and to determine the mirror urls.
    """

    formats = [
        'repodata/repomd.xml.bz2',
        'repodata/repomd.xml.gz',
        'repodata/repomd.xml',
        'suse/repodata/repomd.xml.bz2',
        'suse/repodata/repomd.xml.gz',
        'suse/repodata/repomd.xml',
        'content',
    ]

    if lzma is not None:
        formats.insert(0, 'repodata/repomd.xml.xz')
        formats.insert(4, 'suse/repodata/repomd.xml.xz')

    mirrorlists_check(repo)
    ts = datetime.now().replace(microsecond=0)

    for mirror in repo.mirror_set.filter(mirrorlist=False, refresh=True):

        res = find_mirror_url(mirror.url, formats)
        mirror.last_access_ok = response_is_valid(res)

        if mirror.last_access_ok:
            data = download_url(res, 'Downloading repo info (1/2):')
            if data is None:
                mirror.fail()
                return
            mirror_url = res.url
            if res.url.endswith('content'):
                text = 'Found yast rpm repo - {0!s}'.format(mirror_url)
                info_message.send(sender=None, text=text)
                refresh_yast_repo(mirror, data)
            else:
                text = 'Found yum rpm repo - {0!s}'.format(mirror_url)
                info_message.send(sender=None, text=text)
                refresh_yum_repo(mirror, data, mirror_url, ts)
            mirror.timestamp = ts
        else:
            mirror.fail()
        mirror.save()


def refresh_deb_repo(repo):
    """ Refresh a debian repo.
        Checks for the Packages* files to determine what the mirror urls
        are and then downloads and extracts packages from those files.
    """

    formats = ['Packages.bz2', 'Packages.gz', 'Packages']
    if lzma is not None:
        formats.insert(0, 'Packages.xz')

    for mirror in repo.mirror_set.filter(refresh=True):
        res = find_mirror_url(mirror.url, formats)
        mirror.last_access_ok = response_is_valid(res)

        if mirror.last_access_ok:
            mirror_url = res.url
            text = 'Found deb repo - {0!s}'.format(mirror_url)
            info_message.send(sender=None, text=text)
            data = download_url(res, 'Downloading repo info:')
            if data is None:
                mirror.fail()
                return
            sha1 = get_sha1(data)
            if mirror.file_checksum == sha1:
                text = 'Mirror checksum has not changed, '
                text += 'not refreshing package metadata'
                warning_message.send(sender=None, text=text)
            else:
                packages = extract_deb_packages(data, mirror_url)
                mirror.last_access_ok = True
                mirror.timestamp = datetime.now()
                update_mirror_packages(mirror, packages)
                mirror.file_checksum = sha1
                packages.clear()
        else:
            mirror.fail()
        mirror.save()


def find_best_repo(package, hostrepos):
    """ Given a package and a set of HostRepos, determine the best
        repo. Returns the best repo.
    """
    best_repo = None
    package_repos = hostrepos.filter(repo__mirror__packages=package)

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
