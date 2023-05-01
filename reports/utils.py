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

from django.db import IntegrityError, DatabaseError, transaction

from hosts.models import HostRepo
from arch.models import MachineArchitecture, PackageArchitecture
from repos.models import Repository, Mirror, MirrorPackage
from modules.models import Module
from packages.models import Package
from packages.utils import find_evr, get_or_create_package, \
    get_or_create_package_update, parse_package_string
from patchman.signals import progress_info_s, progress_update_s, \
    error_message, info_message


def process_repos(report, host):
    """ Processes the quoted repos string sent with a report
    """
    if report.repos:
        repo_ids = []
        host_repos = HostRepo.objects.filter(host=host)
        repos = parse_repos(report.repos)

        progress_info_s.send(sender=None,
                             ptext=f'{str(host)[0:25]!s} repos',
                             plen=len(repos))
        for i, repo_str in enumerate(repos):
            repo, priority = process_repo(repo_str, report.arch)
            if repo:
                repo_ids.append(repo.id)
                try:
                    with transaction.atomic():
                        hostrepo, c = host_repos.get_or_create(host=host,
                                                               repo=repo)
                except IntegrityError as e:
                    error_message.send(sender=None, text=e)
                    hostrepo = host_repos.get(host=host, repo=repo)
                try:
                    if hostrepo.priority != priority:
                        hostrepo.priority = priority
                        with transaction.atomic():
                            hostrepo.save()
                except IntegrityError as e:
                    error_message.send(sender=None, text=e)
            progress_update_s.send(sender=None, index=i + 1)

        for hostrepo in host_repos:
            if hostrepo.repo_id not in repo_ids:
                hostrepo.delete()


def process_modules(report, host):
    """ Processes the quoted modules string sent with a report
    """
    if report.modules:
        module_ids = []
        modules = parse_modules(report.modules)

        progress_info_s.send(sender=None,
                             ptext=f'{str(host)[0:25]!s} modules',
                             plen=len(modules))
        for i, module_str in enumerate(modules):
            module = process_module(module_str)
            if module:
                module_ids.append(module.id)
                try:
                    with transaction.atomic():
                        host.modules.add(module)
                except IntegrityError as e:
                    error_message.send(sender=None, text=e)
                except DatabaseError as e:
                    error_message.send(sender=None, text=e)
            progress_update_s.send(sender=None, index=i + 1)

        for module in host.modules.all():
            if module.id not in module_ids:
                host.modules.remove(module)


def process_packages(report, host):
    """ Processes the quoted packages string sent with a report
    """
    if report.packages:
        package_ids = []

        packages = parse_packages(report.packages)
        progress_info_s.send(sender=None,
                             ptext=f'{str(host)[0:25]!s} packages',
                             plen=len(packages))
        for i, pkg_str in enumerate(packages):
            package = process_package(pkg_str, report.protocol)
            if package:
                package_ids.append(package.id)
                try:
                    with transaction.atomic():
                        host.packages.add(package)
                except IntegrityError as e:
                    error_message.send(sender=None, text=e)
                except DatabaseError as e:
                    error_message.send(sender=None, text=e)
            else:
                if pkg_str[0].lower() != 'gpg-pubkey':
                    text = f'No package returned for {pkg_str!s}'
                    info_message.send(sender=None, text=text)
            progress_update_s.send(sender=None, index=i + 1)

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
        ptext = f'{str(host)[0:25]!s} updates'
        progress_info_s.send(sender=None, ptext=ptext, plen=ulen)

        for i, (u, sec) in enumerate(updates.items()):
            update = process_update(host, u, sec)
            if update:
                host.updates.add(update)
            progress_update_s.send(sender=None, index=i + 1)


def parse_updates(updates_string, security):
    """ Parses updates string in a report and returns a sanitized version
        specifying whether it is a security update or not
    """
    updates = {}
    ulist = updates_string.lower().split()
    while ulist:
        name = f'{ulist[0]!s} {ulist[1]!s} {ulist[2]!s}\n'
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
    package = get_or_create_package(name=p_name,
                                    epoch=p_epoch,
                                    version=p_version,
                                    release=p_release,
                                    arch=p_arch,
                                    p_type='R')
    try:
        repo = Repository.objects.get(repo_id=repo_id)
    except Repository.DoesNotExist:
        repo = None
    if repo:
        for mirror in repo.mirror_set.all():
            with transaction.atomic():
                MirrorPackage.objects.create(mirror=mirror, package=package)

    installed_packages = host.packages.filter(name=package.name,
                                              arch=package.arch,
                                              packagetype='R')
    if installed_packages:
        installed_package = installed_packages[0]
        update = get_or_create_package_update(oldpackage=installed_package,
                                              newpackage=package,
                                              security=security)
        return update


def parse_repos(repos_string):
    """ Parses repos string in a report and returns a sanitized version
    """
    repos = []
    for r in [s for s in repos_string.splitlines() if s]:
        repodata = re.findall('\'.*?\'', r)
        for i, rs in enumerate(repodata):
            repodata[i] = rs.replace('\'', '')
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

    if repo[1]:
        r_name = repo[1]

    machine_arches = MachineArchitecture.objects.all()
    with transaction.atomic():
        r_arch, c = machine_arches.get_or_create(name=arch)

    unknown = []
    for r_url in repo[3:]:
        try:
            mirror = Mirror.objects.get(url=r_url)
        except Mirror.DoesNotExist:
            if repository:
                Mirror.objects.create(repo=repository, url=r_url)
            else:
                unknown.append(r_url)
        else:
            repository = mirror.repo
    if not repository:
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

    if r_id and repository.repo_id != r_id:
        repository.repo_id = r_id
        with transaction.atomic():
            repository.save()

    for url in unknown:
        Mirror.objects.create(repo=repository, url=url)

    for mirror in Mirror.objects.filter(repo=repository).values('url'):
        if mirror['url'].find('cdn.redhat.com') != -1 or \
                mirror['url'].find('nu.novell.com') != -1 or \
                mirror['url'].find('updates.suse.com') != -1:
            repository.auth_required = True
            with transaction.atomic():
                repository.save()
        if mirror['url'].find('security') != -1:
            repository.security = True
            with transaction.atomic():
                repository.save()

    return repository, r_priority


def parse_modules(modules_string):
    """ Parses modules string in a report and returns a sanitized version
    """
    modules = []
    for module in modules_string.splitlines():
        module_string = [m for m in module.replace('\'', '').split(' ') if m]
        if module_string:
            modules.append(module_string)
    return modules


def process_module(module_str):
    """ Processes a single sanitied module string and converts to a module
    """
    m_name = module_str[0]
    m_stream = module_str[1]
    m_version = module_str[2]
    m_context = module_str[3]
    arch = module_str[4]
    repo_id = module_str[5]

    package_arches = PackageArchitecture.objects.all()
    with transaction.atomic():
        m_arch, c = package_arches.get_or_create(name=arch)

    try:
        m_repo = Repository.objects.get(repo_id=repo_id)
    except Repository.DoesNotExist:
        m_repo = None

    packages = set()
    for pkg_str in module_str[6:-1]:
        p_type = Package.RPM
        p_name, p_epoch, p_ver, p_rel, p_dist, p_arch = parse_package_string(pkg_str)
        package = get_or_create_package(p_name, p_epoch, p_ver, p_rel, p_arch, p_type)
        packages.add(package)

    modules = Module.objects.all()
    try:
        with transaction.atomic():
            module, c = modules.get_or_create(name=m_name,
                                              stream=m_stream,
                                              version=m_version,
                                              context=m_context,
                                              arch=m_arch,
                                              repo=m_repo)
    except IntegrityError as e:
        error_message.send(sender=None, text=e)
        module = modules.get(name=m_name,
                             stream=m_stream,
                             version=m_version,
                             context=m_context,
                             arch=m_arch,
                             repo=m_repo)
    except DatabaseError as e:
        error_message.send(sender=None, text=e)

    for package in packages:
        try:
            with transaction.atomic():
                module.packages.add(package)
        except IntegrityError as e:
            error_message.send(sender=None, text=e)
        except DatabaseError as e:
            error_message.send(sender=None, text=e)
    return module


def parse_packages(packages_string):
    """ Parses packages string in a report and returns a sanitized version
    """
    packages = []
    for p in packages_string.splitlines():
        packages.append(p.replace('\'', '').split(' '))
    return packages


def process_package(pkg, protocol):
    """ Processes a single sanitized package string and converts to a package
        object
    """
    if protocol == '1':
        epoch = ver = rel = ''
        arch = 'unknown'

        name = pkg[0]
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
        else:
            p_type = Package.UNKNOWN

        package = get_or_create_package(name, epoch, ver, rel, arch, p_type)
        return package
