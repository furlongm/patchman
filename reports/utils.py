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
from packages.models import Package, PackageName, PackageUpdate
from packages.utils import find_evr, get_or_create_package
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
                             ptext='{0!s} repos'.format(str(host)[0:25]),
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
            if hostrepo.repo.id not in repo_ids:
                hostrepo.delete()


def process_packages(report, host):
    """ Processes the quoted packages string sent with a report
    """
    if report.packages:
        package_ids = []

        packages = parse_packages(report.packages)
        progress_info_s.send(sender=None,
                             ptext='{0!s} packages'.format(str(host)[0:25]),
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
                    text = 'No package returned for {0!s}'.format(pkg_str)
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
    add_updates(updates, host)


def merge_updates(sec_updates, bug_updates):
    """ Merge security and non-security updates, removing duplicate
        non-security updates if a security version exists
    """
    for u in sec_updates:
        if u in bug_updates:
            del(bug_updates[u])
    return dict(list(sec_updates.items()) + list(bug_updates.items()))


def add_updates(updates, host):
    """ Add updates to a Host
    """
    for host_update in host.updates.all():
        host.updates.remove(host_update)
    ulen = len(updates)
    if ulen > 0:
        ptext = '{0!s} updates'.format(str(host)[0:25])
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
        name = '{0!s} {1!s} {2!s}\n'.format(ulist[0],
                                            ulist[1],
                                            ulist[2])
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
    package_str = parts[0]
    arch_str = parts[2]

    p_epoch, p_version, p_release = find_evr(update_str[1])

    package_arches = PackageArchitecture.objects.all()
    with transaction.atomic():
        p_arch, c = package_arches.get_or_create(name=arch_str)

    package_names = PackageName.objects.all()
    with transaction.atomic():
        p_name, c = package_names.get_or_create(name=package_str)

    packages = Package.objects.all()
    with transaction.atomic():
        package, c = packages.get_or_create(name=p_name,
                                            arch=p_arch,
                                            epoch=p_epoch,
                                            version=p_version,
                                            release=p_release,
                                            packagetype='R')
    try:
        repo = Repository.objects.get(repo_id=repo_id)
    except Repository.DoesNotExist:
        repo = None
    if repo:
        for mirror in repo.mirror_set.all():
            with transaction.atomic():
                MirrorPackage.objects.create(mirror=mirror, package=package)

    installed_packages = host.packages.filter(name=p_name,
                                              arch=p_arch,
                                              packagetype='R')
    if installed_packages:
        installed_package = installed_packages[0]
        updates = PackageUpdate.objects.all()
        with transaction.atomic():
            update, c = updates.get_or_create(oldpackage=installed_package,
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
