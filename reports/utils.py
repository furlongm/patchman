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

from django.db import IntegrityError

from arch.models import MachineArchitecture, PackageArchitecture
from domains.models import Domain
from hosts.models import HostRepo
from modules.utils import get_or_create_module
from operatingsystems.utils import (
    get_or_create_osrelease, get_or_create_osvariant,
)
from packages.models import Package, PackageCategory
from packages.utils import (
    find_evr, get_or_create_package, get_or_create_package_update,
    parse_package_string,
)
from patchman.signals import pbar_start, pbar_update
from repos.models import Mirror, MirrorPackage, Repository
from repos.utils import get_or_create_repo
from util.logging import debug_message, info_message


def process_repos(report, host):
    """ Processes the quoted repos string sent with a report
    """
    if report.repos:
        repo_ids = []
        host_repos = HostRepo.objects.filter(host=host)
        repos = parse_repos(report.repos)

        pbar_start.send(sender=None, ptext=f'{host} Repos', plen=len(repos))
        for i, repo_str in enumerate(repos):
            debug_message(f'Processing report {report.id} repo: {repo_str}')
            repo, priority = process_repo_text(repo_str, report.arch)
            if repo:
                repo_ids.append(repo.id)
                try:
                    hostrepo, c = host_repos.get_or_create(host=host, repo=repo)
                except IntegrityError:
                    hostrepo = host_repos.get(host=host, repo=repo)
                if hostrepo.priority != priority:
                    hostrepo.priority = priority
                    hostrepo.save()
            pbar_update.send(sender=None, index=i + 1)

        for hostrepo in host_repos:
            if hostrepo.repo_id not in repo_ids:
                hostrepo.delete()


def process_modules(report, host):
    """ Processes the quoted modules string sent with a report
    """
    if report.modules:
        module_ids = []
        modules = parse_modules(report.modules)

        pbar_start.send(sender=None, ptext=f'{host} Modules', plen=len(modules))
        for i, module_str in enumerate(modules):
            module = process_module_text(module_str)
            if module:
                module_ids.append(module.id)
                host.modules.add(module)
            pbar_update.send(sender=None, index=i + 1)

        for module in host.modules.all():
            if module.id not in module_ids:
                host.modules.remove(module)


def process_packages(report, host):
    """ Processes the quoted packages string sent with a report
    """
    if report.packages:
        package_ids = []

        packages = parse_packages(report.packages)
        pbar_start.send(sender=None, ptext=f'{host} Packages', plen=len(packages))
        for i, pkg_str in enumerate(packages):
            debug_message(f'Processing report {report.id} package: {pkg_str}')
            package = process_package_text(pkg_str)
            if package:
                package_ids.append(package.id)
                host.packages.add(package)
            else:
                if pkg_str[0].lower() != 'gpg-pubkey':
                    info_message(text=f'No package returned for {pkg_str}')
            pbar_update.send(sender=None, index=i + 1)

        for package in host.packages.all():
            if package.id not in package_ids:
                host.packages.remove(package)


def process_updates(report, host):
    """ Processes the update strings sent with a report
    """
    bug_updates = {}
    sec_updates = {}
    if report.bug_updates:
        bug_updates = parse_updates(report.bug_updates, False)
    if report.sec_updates:
        sec_updates = parse_updates(report.sec_updates, True)
    updates = merge_updates(sec_updates, bug_updates)
    if updates:
        add_updates(updates, host)


def merge_updates(sec_updates, bug_updates):
    """ Merge security and non-security updates, removing duplicate
        non-security updates if a security version exists
    """
    for u in sec_updates:
        if u in bug_updates:
            del bug_updates[u]
    return dict(list(sec_updates.items()) + list(bug_updates.items()))


def add_updates(updates, host):
    """ Add updates to a Host
    """
    for host_update in host.updates.all():
        host.updates.remove(host_update)
    ulen = len(updates)
    if ulen > 0:
        pbar_start.send(sender=None, ptext=f'{host} Updates', plen=ulen)
        for i, (u, sec) in enumerate(updates.items()):
            update = process_update_text(host, u, sec)
            if update:
                host.updates.add(update)
            pbar_update.send(sender=None, index=i + 1)


def parse_updates(updates_string, security):
    """ Parses updates string in a report and returns a sanitized version
        specifying whether it is a security update or not
    """
    updates = {}
    ulist = updates_string.split()
    while ulist:
        name = f'{ulist[0]} {ulist[1]} {ulist[2]}\n'
        del ulist[:3]
        updates[name] = security
    return updates


def process_update_text(host, update_string, security):
    """ Processes a single sanitized update string and converts to an update
        object. Only works if the original package exists. Returns None otherwise
    """
    update_str = update_string.split()
    repo_id = update_str[2]

    parts = update_str[0].rpartition('.')
    p_name = parts[0]
    p_arch = parts[2]

    p_epoch, p_version, p_release = find_evr(update_str[1])

    return process_update(host, p_name, p_epoch, p_version, p_release, p_arch, repo_id, security)


def process_update(host, name, epoch, version, release, arch, repo_id, security):
    """ Core update processing logic shared by text and JSON handlers
    """
    package = get_or_create_package(
        name=name,
        epoch=epoch,
        version=version,
        release=release,
        arch=arch,
        p_type=Package.RPM
    )
    try:
        repo = Repository.objects.get(repo_id=repo_id)
    except Repository.DoesNotExist:
        repo = None
    if repo:
        for mirror in repo.mirror_set.all():
            MirrorPackage.objects.create(mirror=mirror, package=package)

    installed_packages = host.packages.filter(name=package.name, arch=package.arch, packagetype=Package.RPM)
    if installed_packages:
        installed_package = installed_packages[0]
        update = get_or_create_package_update(oldpackage=installed_package, newpackage=package, security=security)
        return update
    return None


def parse_repos(repos_string):
    """ Parses repos string in a report and returns a sanitized version
    """
    repos = []
    for r in [s for s in repos_string.splitlines() if s]:
        repodata = re.findall(r"'.*?'", r)
        for i, rs in enumerate(repodata):
            repodata[i] = rs.replace("'", '')
        repos.append(repodata)
    return repos


def _get_repo_type(type_str):
    """ Convert repo type string to Repository constant
    """
    type_str = type_str.lower()
    if type_str == 'deb':
        return Repository.DEB
    elif type_str == 'rpm':
        return Repository.RPM
    elif type_str == 'arch':
        return Repository.ARCH
    elif type_str == 'gentoo':
        return Repository.GENTOO
    return None


def process_repo(r_type, r_name, r_id, r_priority, urls, arch):
    """ Core repo processing logic shared by text and JSON handlers
    """
    r_arch, _ = MachineArchitecture.objects.get_or_create(name=arch)

    repository = None
    unknown = []

    for r_url in urls:
        if r_type == Repository.GENTOO and r_url.startswith('rsync'):
            r_url = 'https://api.gentoo.org/mirrors/distfiles.xml'
        try:
            mirror = Mirror.objects.get(url=r_url.strip('/'))
        except Mirror.DoesNotExist:
            if repository:
                Mirror.objects.create(repo=repository, url=r_url.rstrip('/'))
            else:
                unknown.append(r_url)
        else:
            repository = mirror.repo

    if not repository:
        repository = get_or_create_repo(r_name, r_arch, r_type)

    if r_id and repository.repo_id != r_id:
        repository.repo_id = r_id

    if r_name and repository.name != r_name:
        repository.name = r_name

    for url in unknown:
        Mirror.objects.create(repo=repository, url=url.rstrip('/'))

    for mirror in Mirror.objects.filter(repo=repository).values('url'):
        mirror_url = mirror.get('url')
        auth_urls = ['cdn.redhat.com', 'cdn-ubi.redhat.com', 'nu.novell.com', 'updates.suse.com']
        if any(auth_url in mirror_url for auth_url in auth_urls):
            repository.auth_required = True
        if 'security' in mirror_url:
            repository.security = True
    repository.save()

    return repository, r_priority


def process_repo_text(repo, arch):
    """ Processes a single sanitized repo string and converts to a repo object
    """
    r_id = None

    if repo[0] == 'deb':
        r_type = Repository.DEB
        r_priority = int(repo[2])
    elif repo[0] == 'rpm':
        r_type = Repository.RPM
        r_id = repo.pop(2)
        r_priority = int(repo[2]) * -1
    elif repo[0] == 'arch':
        r_type = Repository.ARCH
        r_id = repo[2]
        r_priority = 0
    elif repo[0] == 'gentoo':
        r_type = Repository.GENTOO
        r_id = repo.pop(2)
        r_priority = repo[2]
        arch = 'any'
    else:
        return None, 0

    r_name = repo[1] if repo[1] else ''
    urls = repo[3:]

    return process_repo(r_type, r_name, r_id, r_priority, urls, arch)


def parse_modules(modules_string):
    """ Parses modules string in a report and returns a sanitized version
    """
    modules = []
    for module in modules_string.splitlines():
        module_string = [m for m in module.replace("'", '').split(' ') if m]
        if module_string:
            modules.append(module_string)
    return modules


def process_module(m_name, m_stream, m_version, m_context, m_arch, repo_id, package_strings):
    """ Core module processing logic shared by text and JSON handlers
    """
    arch, _ = PackageArchitecture.objects.get_or_create(name=m_arch)

    try:
        repo = Repository.objects.get(repo_id=repo_id)
    except Repository.DoesNotExist:
        repo = None

    packages = set()
    for pkg_str in package_strings:
        p_type = Package.RPM
        p_name, p_epoch, p_ver, p_rel, p_dist, p_arch = parse_package_string(pkg_str)
        package = get_or_create_package(p_name, p_epoch, p_ver, p_rel, p_arch, p_type)
        packages.add(package)

    module = get_or_create_module(m_name, m_stream, m_version, m_context, arch, repo)
    for package in packages:
        module.packages.add(package)
    return module


def process_module_text(module_str):
    """ Processes a single sanitized module string and converts to a module
    """
    m_name = module_str[0]
    m_stream = module_str[1]
    m_version = module_str[2]
    m_context = module_str[3]
    m_arch = module_str[4]
    repo_id = module_str[5]
    package_strings = module_str[6:]

    return process_module(m_name, m_stream, m_version, m_context, m_arch, repo_id, package_strings)


def parse_packages(packages_string):
    """ Parses packages string in a report and returns a sanitized version
    """
    packages = []
    for p in packages_string.splitlines():
        packages.append(p.replace("'", '').split(' '))
    return packages


def _get_package_type(type_str):
    """ Convert package type string to Package constant
    """
    type_str = type_str.lower() if type_str else ''
    if type_str == 'deb':
        return Package.DEB
    elif type_str == 'rpm':
        return Package.RPM
    elif type_str == 'arch':
        return Package.ARCH
    elif type_str == 'gentoo':
        return Package.GENTOO
    return Package.UNKNOWN


def process_package(name, epoch, version, release, arch, p_type, category=None, repo=None):
    """ Core package processing logic shared by text and JSON handlers
    """
    package = get_or_create_package(name, epoch, version, release, arch, p_type)
    if p_type == Package.GENTOO and category:
        process_gentoo_package(package, name, category, repo)
    return package


def process_package_text(pkg):
    """ Processes a single sanitized package string and converts to a package
        object
    """
    name = pkg[0]
    epoch = pkg[1] if pkg[1] else ''
    ver = pkg[2] if pkg[2] else ''
    rel = pkg[3] if pkg[3] else ''
    arch = pkg[4] if pkg[4] else 'unknown'

    p_type = _get_package_type(pkg[5])
    p_category = pkg[6] if p_type == Package.GENTOO and len(pkg) > 6 else None
    p_repo = pkg[7] if p_type == Package.GENTOO and len(pkg) > 7 else None

    return process_package(name, epoch, ver, rel, arch, p_type, p_category, p_repo)


def process_package_json(pkg):
    """ Processes a single JSON package dict and converts to a package object
    """
    name = pkg['name']
    epoch = pkg.get('epoch', '')
    ver = pkg.get('version', '')
    rel = pkg.get('release', '')
    arch = pkg.get('arch', 'unknown')
    p_type = _get_package_type(pkg.get('type', ''))
    p_category = pkg.get('category') if p_type == Package.GENTOO else None
    p_repo = pkg.get('repo') if p_type == Package.GENTOO else None

    return process_package(name, epoch, ver, rel, arch, p_type, p_category, p_repo)


def process_gentoo_package(package, name, category, repo):
    """ Processes a single gentoo package
    """
    category, created = PackageCategory.objects.get_or_create(name=category)
    package.category = category
    package.save()


def process_packages_json(packages_json, host):
    """ Processes packages from JSON data (protocol 2)
    """
    package_ids = []
    pbar_start.send(sender=None, ptext=f'{host} Packages', plen=len(packages_json))

    for i, pkg in enumerate(packages_json):
        debug_message(f'Processing JSON package: {pkg}')
        package = process_package_json(pkg)
        if package:
            package_ids.append(package.id)
            host.packages.add(package)
        else:
            if pkg.get('name', '').lower() != 'gpg-pubkey':
                info_message(text=f'No package returned for {pkg}')
        pbar_update.send(sender=None, index=i + 1)

    for package in host.packages.all():
        if package.id not in package_ids:
            host.packages.remove(package)


def process_repo_json(repo, arch):
    """ Processes a single JSON repo dict and converts to a repo object
    """
    r_type = _get_repo_type(repo.get('type', ''))
    if r_type is None:
        return None, 0

    if r_type == Repository.GENTOO:
        arch = 'any'

    r_name = repo.get('name', '')
    r_id = repo.get('id', '')
    r_priority = repo.get('priority', 0)
    urls = repo.get('urls', [])

    # Adjust priority for RPM repos (negative)
    if r_type == Repository.RPM:
        r_priority = r_priority * -1

    return process_repo(r_type, r_name, r_id, r_priority, urls, arch)


def process_repos_json(repos_json, host, arch):
    """ Processes repos from JSON data (protocol 2)
    """
    repo_ids = []
    host_repos = HostRepo.objects.filter(host=host)

    pbar_start.send(sender=None, ptext=f'{host} Repos', plen=len(repos_json))
    for i, repo in enumerate(repos_json):
        debug_message(f'Processing JSON repo: {repo}')
        repository, priority = process_repo_json(repo, arch)
        if repository:
            repo_ids.append(repository.id)
            try:
                hostrepo, _ = host_repos.get_or_create(host=host, repo=repository)
            except IntegrityError:
                hostrepo = host_repos.get(host=host, repo=repository)
            if hostrepo.priority != priority:
                hostrepo.priority = priority
                hostrepo.save()
        pbar_update.send(sender=None, index=i + 1)

    for hostrepo in host_repos:
        if hostrepo.repo_id not in repo_ids:
            hostrepo.delete()


def process_module_json(module):
    """ Processes a single JSON module dict and converts to a module object
    """
    m_name = module.get('name')
    m_stream = module.get('stream')
    m_version = module.get('version')
    m_context = module.get('context')
    m_arch = module.get('arch')
    repo_id = module.get('repo', '')
    package_strings = module.get('packages', [])

    return process_module(m_name, m_stream, m_version, m_context, m_arch, repo_id, package_strings)


def process_modules_json(modules_json, host):
    """ Processes modules from JSON data (protocol 2)
    """
    module_ids = []

    pbar_start.send(sender=None, ptext=f'{host} Modules', plen=len(modules_json))
    for i, module in enumerate(modules_json):
        mod = process_module_json(module)
        if mod:
            module_ids.append(mod.id)
            host.modules.add(mod)
        pbar_update.send(sender=None, index=i + 1)

    for mod in host.modules.all():
        if mod.id not in module_ids:
            host.modules.remove(mod)


def process_update_json(host, update, security):
    """ Processes a single JSON update dict and converts to an update object
    """
    name = update.get('name')
    version = update.get('version')
    arch = update.get('arch')
    repo_id = update.get('repo', '')

    p_epoch, p_version, p_release = find_evr(version)

    return process_update(host, name, p_epoch, p_version, p_release, arch, repo_id, security)


def process_updates_json(sec_updates_json, bug_updates_json, host):
    """ Processes updates from JSON data (protocol 2)
    """
    # Clear existing updates
    for host_update in host.updates.all():
        host.updates.remove(host_update)

    # Merge updates, preferring security over bugfix
    sec_keys = {(u['name'], u['arch']) for u in sec_updates_json}
    bug_updates_filtered = [u for u in bug_updates_json if (u['name'], u['arch']) not in sec_keys]

    all_updates = [(u, True) for u in sec_updates_json] + [(u, False) for u in bug_updates_filtered]

    if all_updates:
        pbar_start.send(sender=None, ptext=f'{host} Updates', plen=len(all_updates))
        for i, (update, security) in enumerate(all_updates):
            update_obj = process_update_json(host, update, security)
            if update_obj:
                host.updates.add(update_obj)
            pbar_update.send(sender=None, index=i + 1)


def get_arch(arch):
    """ Get or create MachineArchitecture from arch
        Returns the MachineArchitecture
    """
    return MachineArchitecture.objects.get_or_create(name=arch)[0]


def get_os(os, arch):
    """ Get or create OSRelease and OSVariant from os details
        Returns the OSVariant
    """
    cpe_name = codename = osrelease_codename = osvariant_codename = None
    osrelease_name = osvariant_name = os

    # find cpe_name if it exists
    match = re.match(r'(.*) \[(.*)\]', os)
    if match:
        os = match.group(1)
        cpe_name = match.group(2)

    # find codename if it exists
    match = re.match(r'(.*) \((.*)\)', os)
    if match:
        os = match.group(1)
        codename = match.group(2)
        if os.startswith('AlmaLinux'):
            # alma changes the codename with each minor release, so it's useless to us now
            osvariant_codename = codename
        else:
            osrelease_codename = codename

    osrelease_name = os
    osvariant_name = os

    if os.startswith('Gentoo'):
        osrelease_name = 'Gentoo Linux'
        cpe_name = 'cpe:2.3:o:gentoo:linux:-:*:*:*:*:*:*:*'
    elif os.startswith('Arch'):
        cpe_name = 'cpe:2.3:o:archlinux:arch_linux:-:*:*:*:*:*:*:*'
    elif os.startswith('Debian'):
        major, minor = os.split(' ')[1].split('.')
        osrelease_name = f'Debian {major}'
        cpe_name = f'cpe:2.3:o:debian:debian_linux:{major}.0:*:*:*:*:*:*:*'
    elif os.startswith('Ubuntu'):
        lts = ''
        if 'LTS' in os:
            lts = ' LTS'
        major, minor, patch = os.split(' ')[1].split('.')
        ubuntu_version = f'{major}_{minor}'
        osrelease_name = f'Ubuntu {major}.{minor}{lts}'
        cpe_name = f"cpe:2.3:o:canonical:ubuntu_linux:{ubuntu_version}:*:*:*:{'lts' if lts else '*'}:*:*:*"
    elif os.startswith('AlmaLinux'):
        osvariant_name = os.replace('AlmaLinux', 'Alma Linux')
        osrelease_name = osvariant_name.split('.')[0]
    elif os.startswith('Rocky'):
        osvariant_name = os
        osrelease_name = osvariant_name.split('.')[0]
    elif os.startswith('Red Hat'):
        osvariant_name = os.replace(' release', '')
        osrelease_name = osvariant_name.split('.')[0]
    elif os.startswith('Fedora'):
        osvariant_name = os.replace(' release', '')
        osrelease_name = osvariant_name.split('.')[0]
    elif os.startswith('CentOS'):
        osvariant_name = os.replace(' release', '')
        osrelease_name = osvariant_name.split('.')[0]
    elif os.startswith('Oracle'):
        osvariant_name = os.replace(' Server', '')
        osrelease_name = osvariant_name.split('.')[0]
    elif os.startswith('Amazon Linux AMI 2018.03'):
        osrelease_name = osvariant_name = 'Amazon Linux 1'

    osrelease = get_or_create_osrelease(name=osrelease_name, codename=osrelease_codename, cpe_name=cpe_name)
    osvariant = get_or_create_osvariant(
        name=osvariant_name,
        osrelease=osrelease,
        codename=osvariant_codename,
        arch=arch,
    )
    return osvariant


def get_domain(report_domain):
    if not report_domain:
        report_domain = 'unknown'
    domain, c = Domain.objects.get_or_create(name=report_domain)
    return domain
