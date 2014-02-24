# Copyright 2012 VPAC, http://www.vpac.org
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
import bz2
import gzip
import httplib
from datetime import datetime
from hashlib import sha1, sha256
from StringIO import StringIO
from lxml import etree
from urllib2 import Request, urlopen
from debian.debian_support import Version
from debian.deb822 import Sources

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "patchman.settings")
from django.conf import settings
from django.db.models import Q

from packages.models import Package, PackageName, PackageString
from arch.models import PackageArchitecture
from util import download_url
from signals import info_message, error_message, debug_message, \
    progress_info_s, progress_update_s


def update_mirror_packages(mirror, packages):
    """ Updates the packages contained on a mirror, and
        removes obsolete packages.
    """

    new = set()
    old = set()
    removed = set()

    repopackages = mirror.packages.all()
    rplen = repopackages.count()

    ptext = 'Obtaining stored packages: '
    progress_info_s.send(sender=None, ptext=ptext, plen=rplen)
    for i, package in enumerate(repopackages):
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
    removed = old.difference(packages)

    nlen = len(new)
    rlen = len(removed)

    ptext = 'Removing %s obsolete packages:' % rlen
    progress_info_s.send(sender=None, ptext=ptext, plen=rlen)
    for i, package in enumerate(removed):
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
        MirrorPackage.objects.get(mirror=mirror, package=p).delete()
    mirror.save()

    ptext = 'Adding %s new packages:' % nlen
    progress_info_s.send(sender=None, ptext=ptext, plen=nlen)
    for i, package in enumerate(new):
        progress_update_s.send(sender=None, index=i + 1)

        package_names = PackageName.objects.select_for_update()
        package_id, c = package_names.get_or_create(name=package.name)

        epoch = package.epoch
        version = package.version
        release = package.release
        packagetype = package.packagetype

        package_arches = PackageArchitecture.objects.select_for_update()
        arch, c = package_arches.get_or_create(name=package.arch)

        all_packages = Package.objects.select_for_update()
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
            package_id.save()
        from repos.models import MirrorPackage
        MirrorPackage.objects.create(mirror=mirror, package=p)
    mirror.save()


def gunzip(contents):

    try:
        gzipdata = gzip.GzipFile(fileobj=contents)
        gzipdata = gzipdata.read()
        contents = StringIO(gzipdata)
    except IOError, e:
        import warnings
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        if e.message == 'Not a gzipped file':
            pass

    return contents.getvalue()


def bunzip2(contents):

    try:
        bzip2data = bz2.decompress(contents)
        return bzip2data
    except IOError, e:
        if e == 'invalid data stream':
            pass
    except ValueError, e:
        if e == 'couldn\'t find end of stream':
            pass


def extract(data):

    extracted = bunzip2(data)
    if not extracted:
        extracted = gunzip(StringIO(data))
    return extracted


def get_primary_url(repo_url, data):

    ns = 'http://linux.duke.edu/metadata/repo'
    context = etree.parse(StringIO(data), etree.XMLParser())
    location = context.xpath("//ns:data[@type='primary']/ns:location/@href",
                             namespaces={'ns': ns})[0]
    checksum = context.xpath("//ns:data[@type='primary']/ns:checksum",
                             namespaces={'ns': ns})[0].text
    csum_type = context.xpath("//ns:data[@type='primary']/ns:checksum/@type",
                              namespaces={'ns': ns})[0]
    primary_url = str(repo_url.rsplit('/', 2)[0]) + '/' + location
    return primary_url, checksum, csum_type


def get_sha1(data):

    return sha1(data).hexdigest()


def get_sha256(data):

    return sha256(data).hexdigest()


def get_url(url):

    try:
        res = urlopen(url=Request(url), timeout=10)
        # don't blindly succeed with http 200 (e.g. sourceforge)
        headers = dict(res.headers.items())
        if 'content-type' in headers and \
           not re.match('text/html', headers['content-type']):
            return res
        else:
            return -1
    except IOError, e:
        if hasattr(e, 'reason'):
            debug_message.send(sender=None, text='%s - %s\n' % (url, e.reason))
            return -1
        elif hasattr(e, 'code'):
            debug_message.send(sender=None, text='%s - %s\n' % (url, e))
            return e.code
        else:
            text = 'Unknown error: %s - %s\n' % (url, e)
            error_message.send(sender=None, text=text)
            return -1
    except httplib.BadStatusLine, e:
        text = 'http bad status line: %s - %s\n' % (url, e.line)
        error_message.send(sender=None, text=text)
        return -1


def find_mirror_url(stored_mirror_url, formats):
    """ Find the actual URL of the mirror by trying predefined paths
    """

    yast = False

    for fmt in formats:
        mirror_url = stored_mirror_url
        for f in formats:
            if mirror_url.endswith(f):
                mirror_url = mirror_url[:-len(f)]
        mirror_url = mirror_url.rstrip('/') + '/' + fmt
        res = get_url(mirror_url)
        if type(res) != int:
            break
    if fmt == 'content':
        yast = True
    return mirror_url, res, yast


def check_response(res):

    if type(res) == int:
        return False
    else:
        return True


def mirrorlist_check(mirror_url):
    """ Checks if a given url returns a mirrorlist.
        Does this by checking if it is of type text/plain
        and contains a list of urls
    """

    res = get_url(mirror_url)
    if type(res) != int:
        headers = dict(res.headers.items())
        if 'content-type' in headers and \
           re.match('text/plain', headers['content-type']) is not None:
            data = download_url(res, 'Downloading repo info:')
            if data is None:
                return
            mirror_urls = re.findall('^http://.*$|^ftp://.*$',
                                     data, re.MULTILINE)
            if len(mirror_urls) > 0:
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
            text = 'Found mirrorlist - %s\n' % mirror.url
            info_message.send(sender=None, text=text)
            for mirror_url in mirror_urls:
                mirror_url = mirror_url.replace('$ARCH', repo.arch.name)
                mirror_url = mirror_url.replace('$basearch', repo.arch.name)
                if hasattr(settings, 'MAX_MIRRORS') and \
                        type(settings.MAX_MIRRORS) == int:
                    max_mirrors = settings.MAX_MIRRORS
                    # only add X mirrors, where X = max_mirrors
                    q = Q(mirrorlist=False, refresh=True)
                    existing = mirror.repo.mirror_set.filter(q).count()
                    if existing >= max_mirrors:
                        text = '%s mirrors already exist, not adding %s\n' \
                            % (max_mirrors, mirror_url)
                        info_message.send(sender=None, text=text)
                        continue
                from repos.models import Mirror
                m, c = Mirror.objects.get_or_create(repo=repo, url=mirror_url)
                if c:
                    text = 'Added mirror - %s\n' % mirror_url
                    info_message.send(sender=None, text=text)


def extract_yum_packages(data):
    """ Unpack package metadata from a yum primary.xml file
    """

    extracted = extract(data)
    ns = 'http://linux.duke.edu/metadata/common'
    context = etree.iterparse(StringIO(extracted), tag='{%s}metadata' % ns)
    plen = int(context.next()[1].get('packages'))
    context = etree.iterparse(StringIO(extracted), tag='{%s}package' % ns)

    if plen > 0:
        packages = set()
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
        return packages
    else:
        info_message.send(sender=None, text='No packages found in repo.\n')
    return


def extract_deb_packages(data, packages):
    """ Extract package metadata from debian Packages file
    """

    extracted = extract(data)
    package_re = re.compile('^Package: ', re.M)
    plen = len(package_re.findall(extracted))

    if plen > 0:
        ptext = 'Extracting packages: '
        progress_info_s.send(sender=None, ptext=ptext, plen=plen)

        sio = StringIO(extracted)
        for i, stanza in enumerate(Sources.iter_paragraphs(sio)):
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
        info_message.send(sender=None, text='No packages found in repo.\n')


def extract_yast_packages(data):
    """ Extract package metadata from yast metadata file
    """

    extracted = extract(data)
    pkgs = re.findall('=Pkg: (.*)', extracted)
    plen = len(pkgs)

    if plen > 0:
        packages = set()
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
        return packages
    else:
        info_message.send(sender=None, text='No packages found in repo.\n')
    return


def update_yum_repo(mirror, data, repo_url, ts):
    """ Update package metadata for a yum-style rpm mirror
        and add the packages to the mirror
    """

    primary_url, checksum, checksum_type = get_primary_url(repo_url, data)

    if not primary_url:
        mirror.fail()
        return

    res = get_url(primary_url)
    mirror.last_access_ok = check_response(res)
    if mirror.last_access_ok:
        data = download_url(res, 'Downloading repo info (2/2):')
        if data is None:
            mirror.fail()
            return

        valid = checksum_is_valid(mirror, checksum, checksum_type, data)
        if valid and hasattr(settings, 'MAX_MIRRORS') and \
                type(settings.MAX_MIRRORS) == int:
            max_mirrors = settings.MAX_MIRRORS
            # only refresh X mirrors, where X = max_mirrors
            checksum_q = Q(mirrorlist=False, refresh=True, timestamp=ts)
            have_checksum = mirror.repo.mirror_set.filter(checksum_q).count()
            if have_checksum >= max_mirrors:
                text = '%s mirrors already have this checksum, ignoring refresh to save time\n' % max_mirrors
                info_message.send(sender=None, text=text)
            else:
                packages = extract_yum_packages(data)
                if packages:
                    update_mirror_packages(mirror, packages)
    else:
        mirror.fail()


def checksum_is_valid(mirror, checksum, checksum_type, data):
    """ Check the checksum of the data, returns True if checksum is valid, or
        False if it is invalid or if it has not changed.
    """

    if checksum_type == 'sha':
        sha = get_sha1(data)
    elif checksum_type == 'sha256':
        sha = get_sha256(data)
    else:
        text = 'Unknown checksum type: %s\n' % checksum_type
        error_message.send(sender=None, text=text)

    if sha != checksum:
        text = '%s checksum failed for mirror %s, not updating package metadata\n' % (checksum_type, mirror.id)
        error_message.send(sender=None, text=text)
        mirror.last_access_ok = False
        return False
    elif mirror.file_checksum == sha:
        text = 'Mirror checksum has not changed, not updating package metadata\n'
        info_message.send(sender=None, text=text)
        return False
    return True


def update_yast_repo(mirror, data, repo_url):
    """ Update package metadata for a yast-style rpm mirror
        and add the packages to the mirror
    """

    package_dir = re.findall('DESCRDIR *(.*)', data)[0]
    package_url = '%s/%s/packages.gz' % (mirror.url, package_dir)
    res = get_url(package_url)
    mirror.last_access_ok = check_response(res)
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


def update_rpm_repo(repo):
    """ Update an rpm repo.
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
        'content'
    ]

    mirrorlists_check(repo)
    ts = datetime.now().replace(microsecond=0)

    for mirror in repo.mirror_set.filter(mirrorlist=False, refresh=True):

        repo_url, res, yast = find_mirror_url(mirror.url, formats)
        mirror.last_access_ok = check_response(res)

        if mirror.last_access_ok:
            data = download_url(res, 'Downloading repo info (1/2):')
            if data is None:
                mirror.fail()
                return
            if not yast:
                text = 'Found yum rpm repo - %s\n' % repo_url
                debug_message.send(sender=None, text=text)
                update_yum_repo(mirror, data, repo_url, ts)
            else:
                text = 'Found yast rpm repo - %s\n' % repo_url
                debug_message.send(sender=None, text=text)
                update_yast_repo(mirror, data, repo_url)
            mirror.timestamp = ts
        else:
            mirror.fail()
        mirror.save()


def update_deb_repo(repo):
    """ Update a debian repo.
        Checks for the Packages* files to determine what the mirror urls
        are and then downloads and extracts packages from those files.
    """

    formats = ['Packages.bz2', 'Packages.gz', 'Packages']

    for mirror in repo.mirror_set.filter(refresh=True):
        repo_url, res, unused = find_mirror_url(mirror.url, formats)
        mirror.last_access_ok = check_response(res)

        if mirror.last_access_ok:
            text = 'Found deb repo - %s\n' % repo_url
            debug_message.send(sender=None, text=text)
            data = download_url(res, 'Downloading repo info:')
            if data is None:
                mirror.fail()
                return
            sha1 = get_sha1(data)
            if mirror.file_checksum == sha1:
                text = 'Mirror checksum has not changed, not updating package metadata\n'
                info_message.send(sender=None, text=text)
            else:
                packages = set()
                extract_deb_packages(data, packages)
                mirror.last_access_ok = True
                mirror.timestamp = datetime.now()
                update_mirror_packages(mirror, packages)
                mirror.file_checksum = sha1
                packages.clear()
        else:
            mirror.fail()
        mirror.save()
