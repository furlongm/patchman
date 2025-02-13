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

import io
import os
import git
import re
import shutil
import tarfile
import tempfile
import yaml
from datetime import datetime
from io import BytesIO
from defusedxml.lxml import _etree as etree
from debian.debian_support import Version
from debian.deb822 import Packages
from fnmatch import fnmatch
from tenacity import RetryError

from django.conf import settings
from django.db import IntegrityError, DatabaseError, transaction
from django.db.models import Q

from packages.models import Package, PackageString
from packages.utils import parse_package_string, get_or_create_package, find_evr, \
    convert_package_to_packagestring, convert_packagestring_to_package
from arch.models import PackageArchitecture
from util import get_url, download_url, response_is_valid, extract, \
    get_checksum, Checksum, has_setting_of_type
from patchman.signals import progress_info_s, progress_update_s, \
    info_message, warning_message, error_message, debug_message


def get_or_create_repo(r_name, r_arch, r_type, r_id=None):
    """ Get or create a Repository object. Returns the object. Returns None if
        it cannot get or create the object.
    """
    from repos.models import Repository
    repositories = Repository.objects.all()
    try:
        with transaction.atomic():
            repository, c = repositories.get_or_create(name=r_name,
                                                       arch=r_arch,
                                                       repotype=r_type)
    except IntegrityError as e:
        error_message.send(sender=None, text=e)
        repository = repositories.get(name=r_name,
                                      arch=r_arch,
                                      repotype=r_type)
    except DatabaseError as e:
        error_message.send(sender=None, text=e)
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
    mlen = mirror_packages.count()
    ptext = 'Fetching existing packages:'
    progress_info_s.send(sender=None, ptext=ptext, plen=mlen)
    for i, package in enumerate(mirror_packages):
        progress_update_s.send(sender=None, index=i + 1)
        strpackage = convert_package_to_packagestring(package)
        old.add(strpackage)

    removals = old.difference(packages)
    rlen = len(removals)
    ptext = f'Removing {rlen} obsolete packages:'
    progress_info_s.send(sender=None, ptext=ptext, plen=rlen)
    for i, strpackage in enumerate(removals):
        progress_update_s.send(sender=None, index=i + 1)
        package = convert_packagestring_to_package(strpackage)
        MirrorPackage.objects.filter(mirror=mirror, package=package).delete()

    new = packages.difference(old)
    nlen = len(new)
    ptext = f'Adding {nlen} new packages:'
    progress_info_s.send(sender=None, ptext=ptext, plen=nlen)
    for i, strpackage in enumerate(new):
        progress_update_s.send(sender=None, index=i + 1)
        package = convert_packagestring_to_package(strpackage)
        with transaction.atomic():
            mirror_package, c = MirrorPackage.objects.get_or_create(mirror=mirror, package=package)
    mirror.save()


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
        debug_message.send(sender=None, text=f'Checking for mirror at {mirror_url}')
        try:
            res = get_url(mirror_url)
        except RetryError:
            return
        if res is not None and res.ok:
            return res


def get_gentoo_mirror_urls():
    """ Use the Gentoo API to find http(s) mirrors
    """
    res = get_url('https://api.gentoo.org/mirrors/distfiles.xml')
    if not res:
        return
    mirrors = {}
    tree = etree.parse(BytesIO(res.content))
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
    mirror_urls = []
    # for now, ignore region data and choose MAX_MIRRORS mirrors at random
    for _, v in mirrors.items():
        for url in v['urls']:
            mirror_urls.append(url.rstrip('/') + '/snapshots/gentoo-latest.tar.xz')
    return mirror_urls


def get_gentoo_overlay_mirrors(repo_name):
    """Get the gentoo overlay repos that match repo.id
    """
    res = get_url('https://api.gentoo.org/overlays/repositories.xml')
    if not res:
        return
    tree = etree.parse(BytesIO(res.content))
    root = tree.getroot()
    mirrors = []
    for child in root:
        if child.tag == 'repo':
            found = False
            for element in child:
                if element.tag == 'name' and element.text == repo_name:
                    found = True
                if found and element.tag == 'source':
                    if element.text.startswith('http'):
                        mirrors.append(element.text)
    return mirrors


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
    try:
        res = get_url(url)
    except RetryError:
        return
    if response_is_valid(res):
        if res.headers.get('content-type') == 'text/plain':
            data = download_url(res, 'Downloading repo info:')
            if data is None:
                return
            mirror_urls = re.findall(r'^http[s]*://.*$|^ftp://.*$', data.decode('utf-8'), re.MULTILINE)
            if mirror_urls:
                return mirror_urls


def add_mirrors_from_urls(repo, mirror_urls):
    """ Creates mirrors from a list of mirror urls
    """
    max_mirrors = get_max_mirrors()
    for mirror_url in mirror_urls:
        mirror_url = mirror_url.replace('$ARCH', repo.arch.name)
        mirror_url = mirror_url.replace('$basearch', repo.arch.name)
        q = Q(mirrorlist=False, refresh=True, enabled=True)
        existing = repo.mirror_set.filter(q).count()
        if existing >= max_mirrors:
            text = f'{existing} mirrors already exist (max={max_mirrors}), not adding any more'
            warning_message.send(sender=None, text=text)
            break
        from repos.models import Mirror
        m, c = Mirror.objects.get_or_create(repo=repo, url=mirror_url)
        if c:
            text = f'Added mirror - {mirror_url}'
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
            text = f'Found mirrorlist - {mirror.url}'
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
            text = f'Found metalink - {mirror.url}'
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
        error_message.send(sender=None, text=e)
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
                                tag=f'{{{ns}}}metadata')
    plen = int(next(m_context)[1].get('packages'))
    p_context = etree.iterparse(BytesIO(extracted),
                                tag=f'{{{ns}}}package')
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


def fetch_mirror_data(mirror, url, text, checksum=None, checksum_type=None, metadata_type=None):
    if not url:
        mirror.fail()
        return

    try:
        res = get_url(url)
    except RetryError:
        mirror.fail()
        return

    mirror.last_access_ok = response_is_valid(res)
    if not mirror.last_access_ok:
        mirror.fail()
        return

    data = download_url(res, text)
    if not data:
        mirror.fail()
        return

    if checksum and checksum_type and metadata_type:
        computed_checksum = get_checksum(data, Checksum[checksum_type])
        if not mirror_checksum_is_valid(computed_checksum, checksum, mirror, metadata_type):
            mirror.fail()
            return

    mirror.save()
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


def refresh_yum_repo(mirror, data, mirror_url, ts):
    """ Refresh package metadata for a yum-style rpm mirror
        and add the packages to the mirror
    """
    primary_url, primary_checksum, primary_checksum_type = get_primary_url(mirror_url, data)
    package_data = fetch_mirror_data(
        mirror=mirror,
        url=primary_url,
        checksum=primary_checksum,
        checksum_type=primary_checksum_type,
        text='Downloading package info:',
        metadata_type='package')
    if not package_data:
        return

    if mirror.file_checksum == primary_checksum:
        text = 'Mirror checksum has not changed, not refreshing package metadata'
        warning_message.send(sender=None, text=text)
        return
    else:
        mirror.file_checksum = primary_checksum

    # only refresh X mirrors, where X = max_mirrors
    max_mirrors = get_max_mirrors()
    mirrors_q = Q(mirrorlist=False, refresh=True, enabled=True, timestamp=ts, file_checksum=primary_checksum)
    have_checksum = mirror.repo.mirror_set.filter(mirrors_q).count()
    if have_checksum >= max_mirrors:
        text = f'{max_mirrors} mirrors already have this checksum, skipping refresh'
        info_message.send(sender=None, text=text)
        return

    packages = extract_yum_packages(package_data, primary_url)
    if packages:
        update_mirror_packages(mirror, packages)
        packages.clear()

    modules_url, modules_checksum, modules_checksum_type = get_modules_url(mirror_url, data)
    if modules_url:
        module_data = fetch_mirror_data(
            mirror=mirror,
            url=modules_url,
            checksum=modules_checksum,
            checksum_type=modules_checksum_type,
            text='Downloading module info:',
            metadata_type='module')
        if module_data:
            extract_module_metadata(module_data, modules_url, mirror.repo)

    mirror.save()


def refresh_arch_repo(repo):
    """ Refresh all mirrors of an arch linux repo
    """
    max_mirrors = get_max_mirrors()
    fname = f'{repo.arch}/{repo.repo_id}.db'
    ts = datetime.now().astimezone().replace(microsecond=0)

    enabled_mirrors = repo.mirror_set.filter(refresh=True, enabled=True)
    for i, mirror in enumerate(enabled_mirrors):
        if i >= max_mirrors:
            text = f'{max_mirrors} mirrors already refreshed (max={max_mirrors}), skipping further refreshes'
            warning_message.send(sender=None, text=text)
            break

        res = find_mirror_url(mirror.url, [fname])
        if not res:
            continue
        mirror_url = res.url
        text = f'Found arch repo - {mirror_url}'
        info_message.send(sender=None, text=text)

        package_data = fetch_mirror_data(
            mirror=mirror,
            url=mirror_url,
            text='Downloading repo info:')
        if not package_data:
            continue

        computed_checksum = get_checksum(package_data, Checksum.sha1)
        if mirror.file_checksum == computed_checksum:
            text = 'Mirror checksum has not changed, not refreshing package metadata'
            warning_message.send(sender=None, text=text)
            continue
        else:
            mirror.file_checksum = computed_checksum

        packages = extract_arch_packages(package_data)
        update_mirror_packages(mirror, packages)
        packages.clear()
        mirror.timestamp = ts
        mirror.save()


def refresh_gentoo_main_repo(repo):
    """ Refresh all mirrors of the main gentoo repo
    """
    mirrors = get_gentoo_mirror_urls()
    add_mirrors_from_urls(repo, mirrors)


def refresh_gentoo_overlay_repo(repo):
    """ Refresh all mirrors of a Gentoo overlay repo
    """
    mirrors = get_gentoo_overlay_mirrors(repo.repo_id)
    add_mirrors_from_urls(repo, mirrors)


def get_gentoo_ebuild_keywords(content):
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
    return keywords


def extract_gentoo_packages(mirror, data):
    extracted_files = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode='r') as tar:
        for member in tar.getmembers():
            if member.isfile():
                file_content = tar.extractfile(member).read()
                extracted_files[member.name] = file_content
    packages = set()
    for path, content in extracted_files.items():
        if fnmatch(path, '*.ebuild'):
            components = path.split(os.sep)
            if len(components) < 4:
                continue
            category = components[1]
            name = components[2]
            evr = components[3].replace(f'{name}-', '').replace('.ebuild', '')
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
    return packages


def extract_gentoo_overlay_packages(mirror):
    from packages.utils import find_evr
    t = tempfile.mkdtemp()
    git.Repo.clone_from(mirror.url, t, branch='master', depth=1)
    packages = set()
    with transaction.atomic():
        arch, c = PackageArchitecture.objects.get_or_create(name='any')
    for root, dirs, files in os.walk(t):
        for name in files:
            if fnmatch(name, '*.ebuild'):
                full_name = root.replace(t + '/', '')
                p_category, p_name = full_name.split('/')
                m = re.match(fr'{p_name}-(.*)\.ebuild', name)
                if m:
                    p_evr = m.group(1)
                epoch, version, release = find_evr(p_evr)
                package = PackageString(
                    name=p_name.lower(),
                    epoch=epoch,
                    version=version,
                    release=release,
                    arch=arch,
                    packagetype='G',
                    category=p_category,
                )
                packages.add(package)
    shutil.rmtree(t)
    return packages


def refresh_gentoo_repo(repo):
    """ Refresh a Gentoo repo
    """
    if repo.repo_id == 'gentoo':
        repo_type = 'main'
        refresh_gentoo_main_repo(repo)
    else:
        refresh_gentoo_overlay_repo(repo)
        repo_type = 'overlay'
    ts = datetime.now().replace(microsecond=0)
    for mirror in repo.mirror_set.filter(mirrorlist=False, refresh=True):
        res = get_url(mirror.url + '.md5sum')
        data = download_url(res, 'Downloading repo info (1/2):')
        if data is None:
            mirror.fail()
            continue
        checksum = data.decode().split()[0]
        if checksum is None:
            mirror.fail()
            continue
        if mirror.file_checksum == checksum:
            text = 'Mirror checksum has not changed, not refreshing package metadata'
            warning_message.send(sender=None, text=text)
            continue
        res = get_url(mirror.url)
        mirror.last_access_ok = response_is_valid(res)
        if mirror.last_access_ok:
            data = download_url(res, 'Downloading repo info (2/2):')
            if data is None:
                mirror.fail()
                continue
            extracted = extract(data, mirror.url)
            text = f'Found gentoo repo - {mirror.url}'
            info_message.send(sender=None, text=text)
            computed_checksum = get_checksum(data, Checksum.md5)
            if not mirror_checksum_is_valid(computed_checksum, checksum, mirror, 'package'):
                continue
            else:
                mirror.file_checksum = checksum
            if repo_type == 'main':
                packages = extract_gentoo_packages(mirror, extracted)
            elif repo_type == 'overlay':
                packages = extract_gentoo_overlay_packages(mirror)
            mirror.timestamp = ts
            if packages:
                update_mirror_packages(mirror, packages)
        else:
            mirror.fail()
        mirror.save()


def refresh_yast_repo(mirror, data):
    """ Refresh package metadata for a yast-style rpm mirror
        and add the packages to the mirror
    """
    package_dir = re.findall('DESCRDIR *(.*)', data.decode('utf-8'))[0]
    package_url = f'{mirror.url}/{package_dir}/packages.gz'

    package_data = fetch_mirror_data(
        mirror=mirror,
        url=package_url,
        text='Downloading yast repo info:')
    if not package_data:
        return

    mirror.file_checksum = 'yast'
    packages = extract_yast_packages(package_data)
    if packages:
        update_mirror_packages(mirror, packages)
        packages.clear()


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

    max_mirrors = get_max_mirrors()
    ts = datetime.now().astimezone().replace(microsecond=0)
    enabled_mirrors = repo.mirror_set.filter(mirrorlist=False, refresh=True, enabled=True)
    for i, mirror in enumerate(enabled_mirrors):
        if i >= max_mirrors:
            text = f'{max_mirrors} mirrors already refreshed (max={max_mirrors}), skipping further refreshes'
            warning_message.send(sender=None, text=text)
            break

        res = find_mirror_url(mirror.url, formats)
        if not res:
            continue
        mirror_url = res.url

        repo_data = fetch_mirror_data(
            mirror=mirror,
            url=mirror_url,
            text='Downloading repo info:')
        if not repo_data:
            continue

        if mirror_url.endswith('content'):
            text = f'Found yast rpm repo - {mirror_url}'
            info_message.send(sender=None, text=text)
            refresh_yast_repo(mirror, repo_data)
        else:
            text = f'Found yum rpm repo - {mirror_url}'
            info_message.send(sender=None, text=text)
            refresh_yum_repo(mirror, repo_data, mirror_url, ts)
        mirror.timestamp = ts
        mirror.save()


def refresh_deb_repo(repo):
    """ Refresh a debian repo.
        Checks for the Packages* files to determine what the mirror urls
        are and then downloads and extracts packages from those files.
    """

    formats = ['Packages.xz', 'Packages.bz2', 'Packages.gz', 'Packages']

    ts = datetime.now().astimezone().replace(microsecond=0)
    enabled_mirrors = repo.mirror_set.filter(refresh=True, enabled=True)
    for mirror in enabled_mirrors:
        res = find_mirror_url(mirror.url, formats)
        if not res:
            continue
        mirror_url = res.url
        text = f'Found deb repo - {mirror_url}'
        info_message.send(sender=None, text=text)

        package_data = fetch_mirror_data(
            mirror=mirror,
            url=mirror_url,
            text='Downloading repo info:')
        if not package_data:
            continue

        computed_checksum = get_checksum(package_data, Checksum.sha1)
        if mirror.file_checksum == computed_checksum:
            text = 'Mirror checksum has not changed, not refreshing package metadata'
            warning_message.send(sender=None, text=text)
            continue
        else:
            mirror.file_checksum = computed_checksum

        packages = extract_deb_packages(package_data, mirror_url)
        if not packages:
            mirror.fail()
            continue

        update_mirror_packages(mirror, packages)
        packages.clear()
        mirror.timestamp = ts
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


def get_max_mirrors():
    """ Find the max number of mirrors for refresh
    """
    if has_setting_of_type('MAX_MIRRORS', int):
        max_mirrors = settings.MAX_MIRRORS
    else:
        max_mirrors = 5
    return max_mirrors
