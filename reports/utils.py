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
from operatingsystems.utils import get_or_create_osrelease, get_or_create_osvariant
from packages.models import Package, PackageCategory
from packages.utils import find_evr, get_or_create_package, get_or_create_package_update, parse_package_string
from patchman.signals import pbar_start, pbar_update, info_message
from repos.models import Repository, Mirror, MirrorPackage
from repos.utils import get_or_create_repo


def process_repos(report, host):
    """ Processes the quoted repos string sent with a report
    """
    if report.repos:
        repo_ids = []
        host_repos = HostRepo.objects.filter(host=host)
        repos = parse_repos(report.repos)

        pbar_start.send(sender=None, ptext=f'{host} Repos', plen=len(repos))
        for i, repo_str in enumerate(repos):
            repo, priority = process_repo(repo_str, report.arch)
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
            module = process_module(module_str)
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
            package = process_package(pkg_str, report.protocol)
            if package:
                package_ids.append(package.id)
                host.packages.add(package)
            else:
                if pkg_str[0].lower() != 'gpg-pubkey':
                    info_message.send(sender=None, text=f'No package returned for {pkg_str}')
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
            update = process_update(host, u, sec)
            if update:
                host.updates.add(update)
            pbar_update.send(sender=None, index=i + 1)


def parse_updates(updates_string, security):
    """ Parses updates string in a report and returns a sanitized version
        specifying whether it is a security update or not
    """
    updates = {}
    ulist = updates_string.lower().split()
    while ulist:
        name = f'{ulist[0]} {ulist[1]} {ulist[2]}\n'
        del ulist[:3]
        updates[name] = security
    return updates


def process_update(host, update_string, security):
    """ Processes a single sanitized update string and converts to an update
        object. Only works if the original package exists. Returns None otherwise
    """
    update_str = update_string.split()
    repo_id = update_str[2]

    parts = update_str[0].rpartition('.')
    p_name = parts[0]
    p_arch = parts[2]

    p_epoch, p_version, p_release = find_evr(update_str[1])
    package = get_or_create_package(
        name=p_name,
        epoch=p_epoch,
        version=p_version,
        release=p_release,
        arch=p_arch,
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


def process_repo(repo, arch):
    """ Processes a single sanitized repo string and converts to a repo object
    """
    repository = r_id = None

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

    if repo[1]:
        r_name = repo[1]

    r_arch, c = MachineArchitecture.objects.get_or_create(name=arch)

    unknown = []
    for r_url in repo[3:]:
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


def parse_modules(modules_string):
    """ Parses modules string in a report and returns a sanitized version
    """
    modules = []
    for module in modules_string.splitlines():
        module_string = [m for m in module.replace("'", '').split(' ') if m]
        if module_string:
            modules.append(module_string)
    return modules


def process_module(module_str):
    """ Processes a single sanitized module string and converts to a module
    """
    m_name = module_str[0]
    m_stream = module_str[1]
    m_version = module_str[2]
    m_context = module_str[3]
    m_arch = module_str[4]
    repo_id = module_str[5]

    arch, c = PackageArchitecture.objects.get_or_create(name=m_arch)

    try:
        repo = Repository.objects.get(repo_id=repo_id)
    except Repository.DoesNotExist:
        repo = None

    packages = set()
    for pkg_str in module_str[6:]:
        p_type = Package.RPM
        p_name, p_epoch, p_ver, p_rel, p_dist, p_arch = parse_package_string(pkg_str)
        package = get_or_create_package(p_name, p_epoch, p_ver, p_rel, p_arch, p_type)
        packages.add(package)

    module = get_or_create_module(m_name, m_stream, m_version, m_context, arch, repo)
    for package in packages:
        module.packages.add(package)
    return module


def parse_packages(packages_string):
    """ Parses packages string in a report and returns a sanitized version
    """
    packages = []
    for p in packages_string.splitlines():
        packages.append(p.replace("'", '').split(' '))
    return packages


def process_package(pkg, protocol):
    """ Processes a single sanitized package string and converts to a package
        object
    """
    if protocol == '1':
        epoch = ver = rel = ''
        arch = 'unknown'

        name = pkg[0]
        p_category = p_repo = None
        if pkg[1]:
            epoch = pkg[1]
        if pkg[2]:
            ver = pkg[2]
        if pkg[3]:
            rel = pkg[3]
        if pkg[4]:
            arch = pkg[4]

        if pkg[5] == 'deb':
            p_type = Package.DEB
        elif pkg[5] == 'rpm':
            p_type = Package.RPM
        elif pkg[5] == 'arch':
            p_type = Package.ARCH
        elif pkg[5] == 'gentoo':
            p_type = Package.GENTOO
            p_category = pkg[6]
            p_repo = pkg[7]
        else:
            p_type = Package.UNKNOWN

        package = get_or_create_package(name, epoch, ver, rel, arch, p_type)
        if p_type == Package.GENTOO:
            process_gentoo_package(package, name, p_category, p_repo)
        return package


def process_gentoo_package(package, name, category, repo):
    """ Processes a single gentoo package
    """
    category, created = PackageCategory.objects.get_or_create(name=category)
    package.category = category
    package.save()


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
