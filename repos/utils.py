# Copyright 2012 VPAC, http://www.vpac.org
# Copyright 2013-2021 Marcus Furlong <furlongm@gmail.com>
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
import tarfile
try:
    import lzma
except ImportError:
    try:
        from backports import lzma
    except ImportError:
        lzma = None
from datetime import datetime
from io import BytesIO
from defusedxml.lxml import _etree as etree
from debian.debian_support import Version
from debian.deb822 import Packages

from django.conf import settings
from django.db import transaction
from django.db.models import Q

from packages.models import Package, PackageName, PackageString
from arch.models import PackageArchitecture
from util import get_url, download_url, response_is_valid, extract, \
    get_checksum, Checksum
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
        from repos.models import MirrorPackage
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
        from repos.models import MirrorPackage  # noqa
        with transaction.atomic():
            MirrorPackage.objects.create(mirror=mirror, package=p)


def get_primary_url(mirror_url, data):

    if isinstance(data, str):
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


def is_metalink(url):
    """ Checks if a given url is a metalink url
    """
    return 'metalink?' in url.lower()


def get_metalink_urls(url):
    """  Parses a metalink and returns a list of mirrors
    """
    res = get_url(url)
    if response_is_valid(res):
        if 'content-type' in res.headers and \
           res.headers['content-type'] == 'application/metalink+xml':
            data = download_url(res, 'Downloading repo info:')
            ns = 'http://www.metalinker.org/'
            try:
                context = etree.parse(BytesIO(data), etree.XMLParser())
            except etree.XMLSyntaxError:
                context = etree.parse(BytesIO(extract(data, 'gz')),
                                      etree.XMLParser())
            xpath = "//ns:files/ns:file[@name='repomd.xml']/ns:resources/ns:url[@protocol='https']"  # noqa
            metalink_urls = context.xpath(xpath, namespaces={'ns': ns})
            return [x.text for x in metalink_urls]


def get_mirrorlist_urls(url):
    """ Checks if a given url returns a mirrorlist by checking if it is of
        type text/plain and contains a list of urls. Returns a list of
        mirrors if it is a mirrorlist.
    """
    res = get_url(url)
    if response_is_valid(res):
        if 'content-type' in res.headers and \
           'text/plain' in res.headers['content-type']:
            data = download_url(res, 'Downloading repo info:')
            if data is None:
                return
            mirror_urls = re.findall('^http://.*$|^ftp://.*$',
                                     data.decode('utf-8'), re.MULTILINE)
            if mirror_urls:
                return mirror_urls


def add_mirrors_from_urls(repo, mirror_urls):
    """ Creates mirrors from a list of mirror urls
    """
    for mirror_url in mirror_urls:
        mirror_url = mirror_url.replace('$ARCH', repo.arch.name)
        mirror_url = mirror_url.replace('$basearch', repo.arch.name)
        if hasattr(settings, 'MAX_MIRRORS') and \
                isinstance(settings.MAX_MIRRORS, int):
            max_mirrors = settings.MAX_MIRRORS
            # only add X mirrors, where X = max_mirrors
            q = Q(mirrorlist=False, refresh=True)
            existing = repo.mirror_set.filter(q).count()
            if existing >= max_mirrors:
                text = '{0!s} mirrors already '.format(max_mirrors)
                text += 'exist, not adding {0!s}'.format(mirror_url)
                warning_message.send(sender=None, text=text)
                continue
        from repos.models import Mirror
        m, c = Mirror.objects.get_or_create(repo=repo, url=mirror_url)
        if c:
            text = 'Added mirror - {0!s}'.format(mirror_url)
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
            text = 'Found mirrorlist - {0!s}'.format(mirror.url)
            info_message.send(sender=None, text=text)
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
            text = 'Found metalink - {0!s}'.format(mirror.url)
            info_message.send(sender=None, text=text)
            add_mirrors_from_urls(repo, mirror_urls)


def extract_yum_packages(data, url):
    """ Extract package metadata from a yum primary.xml file
    """
    extracted = extract(data, url)
    ns = 'http://linux.duke.edu/metadata/common'
    m_context = etree.iterparse(BytesIO(extracted),
                                tag='{{{0!s}}}metadata'.format(ns))
    plen = int(next(m_context)[1].get('packages'))
    p_context = etree.iterparse(BytesIO(extracted),
                                tag='{{{0!s}}}package'.format(ns))
    packages = set()

    if plen > 0:
        ptext = 'Extracting packages: '
        progress_info_s.send(sender=None, ptext=ptext, plen=plen)

        for i, p_data in enumerate(p_context):
            elem = p_data[1]
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
    extracted = extract(data, url).decode('utf-8')
    package_re = re.compile('^Package: ', re.M)
    plen = len(package_re.findall(extracted))
    packages = set()

    if plen > 0:
        ptext = 'Extracting packages: '
        progress_info_s.send(sender=None, ptext=ptext, plen=plen)
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
    extracted = extract(data, 'gz').decode('utf-8')
    pkgs = re.findall('=Pkg: (.*)', extracted)
    plen = len(pkgs)
    packages = set()

    if plen > 0:
        ptext = 'Extracting packages: '
        progress_info_s.send(sender=None, ptext=ptext, plen=plen)

        for i, pkg in enumerate(pkgs):
            progress_update_s.send(sender=None, index=i + 1)
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


def extract_arch_packages(data):
    """ Extract package metadata from an arch linux tarfile
    """
    from packages.utils import find_evr
    extracted = BytesIO(extract(data, 'gz'))
    tf = tarfile.open(fileobj=extracted, mode='r:*')
    packages = set()
    plen = len(tf.getnames())
    if plen > 0:
        ptext = 'Extracting packages: '
        progress_info_s.send(sender=None, ptext=ptext, plen=plen)
        for i, tarinfo in enumerate(tf):
            progress_update_s.send(sender=None, index=i + 1)
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

    computed_checksum = get_checksum(data, Checksum[checksum_type])
    if not mirror_checksum_is_valid(computed_checksum, checksum, mirror):
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


def mirror_checksum_is_valid(computed, provided, mirror):
    """ Compares the computed checksum and the provided checksum. Returns True
        if both match.
    """
    if not computed or computed != provided:
        text = 'Checksum failed for mirror {0!s}'.format(mirror.id)
        text += ', not refreshing package metadata'
        error_message.send(sender=None, text=text)
        text = 'Found checksum:    {0!s}\nExpected checksum: {1!s}'.format(
            computed,
            provided
        )
        error_message.send(sender=None, text=text)
        mirror.last_access_ok = False
        mirror.fail()
        return False
    else:
        return True


def refresh_arch_repo(repo):
    """ Refresh all mirrors of an arch linux repo
    """
    if hasattr(settings, 'MAX_MIRRORS') and \
            isinstance(settings.MAX_MIRRORS, int):
        max_mirrors = settings.MAX_MIRRORS
    fname = '{0!s}/{1!s}.db'.format(repo.arch, repo.repo_id)
    ts = datetime.now().replace(microsecond=0)
    for i, mirror in enumerate(repo.mirror_set.filter(refresh=True)):
        res = find_mirror_url(mirror.url, [fname])
        mirror.last_access_ok = response_is_valid(res)
        if mirror.last_access_ok:
            if i >= max_mirrors:
                text = '{0!s} mirrors already refreshed, '.format(max_mirrors)
                text += ' not refreshing {0!s}'.format(mirror.url)
                warning_message.send(sender=None, text=text)
                continue
            mirror_url = res.url
            text = 'Found arch repo - {0!s}'.format(mirror_url)
            info_message.send(sender=None, text=text)
            data = download_url(res, 'Downloading repo info:')
            if data is None:
                mirror.fail()
                return
            computed_checksum = get_checksum(data, Checksum.sha1)
            if mirror.file_checksum == computed_checksum:
                text = 'Mirror checksum has not changed, '
                text += 'not refreshing package metadata'
                warning_message.send(sender=None, text=text)
            else:
                packages = extract_arch_packages(data)
                mirror.last_access_ok = True
                mirror.timestamp = ts
                update_mirror_packages(mirror, packages)
                mirror.file_checksum = computed_checksum
                packages.clear()
        else:
            mirror.fail()
        mirror.save()


def refresh_yast_repo(mirror, data):
    """ Refresh package metadata for a yast-style rpm mirror
        and add the packages to the mirror
    """
    package_dir = re.findall('DESCRDIR *(.*)', data.decode('utf-8'))[0]
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

    check_for_mirrorlists(repo)
    check_for_metalinks(repo)

    if hasattr(settings, 'MAX_MIRRORS') and \
            isinstance(settings.MAX_MIRRORS, int):
        max_mirrors = settings.MAX_MIRRORS
    ts = datetime.now().replace(microsecond=0)
    enabled_mirrors = repo.mirror_set.filter(mirrorlist=False, refresh=True)
    for i, mirror in enumerate(enabled_mirrors):
        res = find_mirror_url(mirror.url, formats)
        mirror.last_access_ok = response_is_valid(res)
        if mirror.last_access_ok:
            if i >= max_mirrors:
                text = '{0!s} mirrors already refreshed, '.format(max_mirrors)
                text += ' not refreshing {0!s}'.format(mirror.url)
                warning_message.send(sender=None, text=text)
                continue
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

    ts = datetime.now().replace(microsecond=0)
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
            computed_checksum = get_checksum(data, Checksum.sha1)
            if mirror.file_checksum == computed_checksum:
                text = 'Mirror checksum has not changed, '
                text += 'not refreshing package metadata'
                warning_message.send(sender=None, text=text)
            else:
                packages = extract_deb_packages(data, mirror_url)
                mirror.last_access_ok = True
                mirror.timestamp = ts
                update_mirror_packages(mirror, packages)
                mirror.file_checksum = computed_checksum
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
