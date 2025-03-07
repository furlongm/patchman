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
import yaml
from datetime import datetime
from io import BytesIO
from defusedxml.lxml import _etree as etree
from debian.debian_support import Version
from debian.deb822 import Packages

from django.conf import settings
from django.db import IntegrityError, DatabaseError, transaction
from django.db.models import Q

from packages.models import Package, PackageName, PackageString
from packages.utils import parse_package_string, get_or_create_package
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

    ptext = 'Fetching existing packages:'
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

    ptext = f'Removing {rlen!s} obsolete packages:'
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
        mirror_packages = MirrorPackage.objects.filter(mirror=mirror, package=p)
        for mirror_package in mirror_packages:
            with transaction.atomic():
                mirror_package.delete()

    ptext = f'Adding {nlen!s} new packages:'
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
            mirror_package, c = MirrorPackage.objects.get_or_create(mirror=mirror, package=p)


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
    url = str(mirror_url.rsplit('/', 2)[0]) + '/' + location
    return url, checksum, csum_type


def get_modules_url(mirror_url, data):

    if isinstance(data, str):
        if data.startswith('Bad repo - not in list') or \
                data.startswith('Invalid repo'):
            return None, None, None
    ns = 'http://linux.duke.edu/metadata/repo'
    try:
        context = etree.parse(BytesIO(data), etree.XMLParser())
    except etree.XMLSyntaxError:
        context = etree.parse(BytesIO(extract(data, 'gz')), etree.XMLParser())
    try:
        location = context.xpath("//ns:data[@type='modules']/ns:location/@href",
                                 namespaces={'ns': ns})[0]
    except IndexError:
        return None, None, None
    checksum = context.xpath("//ns:data[@type='modules']/ns:checksum",
                             namespaces={'ns': ns})[0].text
    csum_type = context.xpath("//ns:data[@type='modules']/ns:checksum/@type",
                              namespaces={'ns': ns})[0]
    url = str(mirror_url.rsplit('/', 2)[0]) + '/' + location
    return url, checksum, csum_type


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
                           text=f'Checking {mirror_url!s}')
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
            mirror_urls = re.findall('^http[s]*://.*$|^ftp://.*$',
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
                text = f'{max_mirrors!s} mirrors already '
                text += f'exist, not adding {mirror_url!s}'
                warning_message.send(sender=None, text=text)
                continue
        from repos.models import Mirror
        m, c = Mirror.objects.get_or_create(repo=repo, url=mirror_url)
        if c:
            text = f'Added mirror - {mirror_url!s}'
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
            text = f'Found mirrorlist - {mirror.url!s}'
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
            text = f'Found metalink - {mirror.url!s}'
            info_message.send(sender=None, text=text)
            add_mirrors_from_urls(repo, mirror_urls)


def extract_module_metadata(data, url, repo):
    """ Extract module metadata from a modules.yaml file
    """
    modules = set()
    extracted = extract(data, url)
    try:
        modules_yaml = yaml.safe_load_all(extracted)
    except yaml.YAMLError as e:
        print(e)
    for doc in modules_yaml:
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
            module, created = get_or_create_module(m_name, m_stream, m_version, m_context, arch, repo)

            package_ids = []
            for package in packages:
                package_ids.append(package.id)
                try:
                    with transaction.atomic():
                        module.packages.add(package)
                except IntegrityError as e:
                    error_message.send(sender=None, text=e)
                except DatabaseError as e:
                    error_message.send(sender=None, text=e)
            modules.add(module)
            for package in module.packages.all():
                if package.id not in package_ids:
                    module.packages.remove(package)


def extract_yum_packages(data, url):
    """ Extract package metadata from a yum primary.xml file
    """
    extracted = extract(data, url)
    ns = 'http://linux.duke.edu/metadata/common'
    m_context = etree.iterparse(BytesIO(extracted),
                                tag=f'{{{ns!s}}}metadata')
    plen = int(next(m_context)[1].get('packages'))
    p_context = etree.iterparse(BytesIO(extracted),
                                tag=f'{{{ns!s}}}package')
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
    try:
        extracted = extract(data, url).decode('utf-8')
    except UnicodeDecodeError as e:
        error_message.send(sender=None, text=f'Skipping {url} : {e}')
        return
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
    bio = BytesIO(data)
    tf = tarfile.open(fileobj=bio, mode='r:*')
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
    primary_url, primary_checksum, primary_checksum_type = get_primary_url(mirror_url, data)
    modules_url, modules_checksum, modules_checksum_type = get_modules_url(mirror_url, data)

    if not primary_url:
        mirror.fail()
        return

    res = get_url(primary_url)
    mirror.last_access_ok = response_is_valid(res)

    if not mirror.last_access_ok:
        mirror.fail()
        return

    package_data = download_url(res, 'Downloading package info:')
    if package_data is None:
        mirror.fail()
        return

    computed_checksum = get_checksum(package_data, Checksum[primary_checksum_type])
    if not mirror_checksum_is_valid(computed_checksum, primary_checksum, mirror, 'package'):
        return

    if mirror.file_checksum == primary_checksum:
        text = 'Mirror checksum has not changed, '
        text += 'not refreshing package metadata'
        warning_message.send(sender=None, text=text)
        return

    mirror.file_checksum = primary_checksum

    if modules_url:
        res = get_url(modules_url)
        module_data = download_url(res, 'Downloading module info:')
        computed_checksum = get_checksum(module_data, Checksum[modules_checksum_type])
        if not mirror_checksum_is_valid(computed_checksum, modules_checksum, mirror, 'module'):
            return

    if hasattr(settings, 'MAX_MIRRORS') and \
            isinstance(settings.MAX_MIRRORS, int):
        max_mirrors = settings.MAX_MIRRORS
        # only refresh X mirrors, where X = max_mirrors
        checksum_q = Q(mirrorlist=False, refresh=True, timestamp=ts,
                       file_checksum=primary_checksum)
        have_checksum = mirror.repo.mirror_set.filter(checksum_q).count()
        if have_checksum >= max_mirrors:
            text = f'{max_mirrors!s} mirrors already have this '
            text += 'checksum, ignoring refresh to save time'
            info_message.send(sender=None, text=text)
        else:
            packages = extract_yum_packages(package_data, primary_url)
            if packages:
                update_mirror_packages(mirror, packages)
            if modules_url:
                extract_module_metadata(module_data, modules_url, mirror.repo)


def mirror_checksum_is_valid(computed, provided, mirror, metadata_type):
    """ Compares the computed checksum and the provided checksum.
        Returns True if both match.
    """
    if not computed or computed != provided:
        text = f'Checksum failed for mirror {mirror.id!s}'
        text += f', not refreshing {metadata_type} metadata'
        error_message.send(sender=None, text=text)
        text = f'Found checksum:    {computed}\nExpected checksum: {provided}'
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
    fname = f'{repo.arch!s}/{repo.repo_id!s}.db'
    ts = datetime.now().replace(microsecond=0)
    for i, mirror in enumerate(repo.mirror_set.filter(refresh=True)):
        res = find_mirror_url(mirror.url, [fname])
        mirror.last_access_ok = response_is_valid(res)
        if mirror.last_access_ok:
            if i >= max_mirrors:
                text = f'{max_mirrors!s} mirrors already refreshed, '
                text += f' not refreshing {mirror.url!s}'
                warning_message.send(sender=None, text=text)
                continue
            mirror_url = res.url
            text = f'Found arch repo - {mirror_url!s}'
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
    package_url = f'{mirror.url!s}/{package_dir!s}/packages.gz'
    res = get_url(package_url)
    mirror.last_access_ok = response_is_valid(res)
    if mirror.last_access_ok:
        data = download_url(res, 'Downloading yast repo info:')
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
                text = f'{max_mirrors!s} mirrors already refreshed, '
                text += f' not refreshing {mirror.url!s}'
                warning_message.send(sender=None, text=text)
                continue
            data = download_url(res, 'Downloading repo info:')
            if data is None:
                mirror.fail()
                return
            mirror_url = res.url
            if res.url.endswith('content'):
                text = f'Found yast rpm repo - {mirror_url!s}'
                info_message.send(sender=None, text=text)
                refresh_yast_repo(mirror, data)
            else:
                text = f'Found yum rpm repo - {mirror_url!s}'
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

    formats = ['Packages.xz', 'Packages.bz2', 'Packages.gz', 'Packages']

    ts = datetime.now().replace(microsecond=0)
    for mirror in repo.mirror_set.filter(refresh=True):
        res = find_mirror_url(mirror.url, formats)
        mirror.last_access_ok = response_is_valid(res)

        if mirror.last_access_ok:
            mirror_url = res.url
            text = f'Found deb repo - {mirror_url!s}'
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
                if packages is None:
                    mirror.fail()
                else:
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
