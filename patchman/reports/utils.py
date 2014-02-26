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

import re

from django.db import IntegrityError, DatabaseError, transaction

from hosts.models import HostRepo
from arch.models import MachineArchitecture, PackageArchitecture
from repos.models import Repository, Mirror, MirrorPackage
from packages.models import Package, PackageName, PackageUpdate
from packages.utils import find_versions
from signals import progress_info_s, progress_update_s


@transaction.commit_manually
def process_repos(report, host):
    """ Processes the quoted repos string sent with a report """

    if report.repos:
        old_repos = host.repos.all()

        repos = parse_repos(report.repos)
        progress_info_s.send(sender=None,
                             ptext='%s repos' % host.__unicode__()[0:25],
                             plen=len(repos))
        for i, repo_str in enumerate(repos):
            repo, priority = process_repo(repo_str, report.arch)
            if repo:
                try:
                    host_repos = HostRepo.objects.select_for_update()
                    hostrepo, c = host_repos.get_or_create(host=host,
                                                           repo=repo)
                    transaction.commit()
                except IntegrityError as e:
                    print e
                    hostrepo = host_repos.get(host=host, repo=repo)
                hostrepo.priority = priority
                try:
                    hostrepo.save()
                    transaction.commit()
                except IntegrityError as e:
                    print e
            progress_update_s.send(sender=None, index=i + 1)

        removals = old_repos.exclude(pk__in=host.repos.all())
        for repo in removals:
            host.repos.remove(repo)
        transaction.commit()
    transaction.commit()


@transaction.commit_manually
def process_packages(report, host):
    """ Processes the quoted packages string sent with a report """

    if report.packages:
        old_packages = host.packages.all()

        packages = parse_packages(report.packages)
        progress_info_s.send(sender=None,
                             ptext='%s packages' % host.__unicode__()[0:25],
                             plen=len(packages))
        for i, pkg_str in enumerate(packages):
            package = process_package(pkg_str, report.protocol)
            if package:
                try:
                    host.packages.add(package)
                    transaction.commit()
                except IntegrityError as e:
                    print e
                except DatabaseError as e:
                    print e
                    transaction.rollback()
            progress_update_s.send(sender=None, index=i + 1)

        removals = old_packages.exclude(pk__in=host.packages.all())
        for package in removals:
            host.packages.remove(package)
    transaction.commit()


def process_updates(report, host):
    """ Processes the update strings sent with a report """

    bug_updates = ''
    sec_updates = ''
    if report.bug_updates:
        bug_updates = parse_updates(report.bug_updates)
        add_updates(bug_updates, host, False)
    if report.sec_updates:
        sec_updates = parse_updates(report.sec_updates)
        add_updates(sec_updates, host, True)


def add_updates(updates, host, security):

    ulen = len(updates)
    if security:
        extra = 'sec'
    else:
        extra = 'bug'

    if ulen > 0:
        ptext = '%s %s updates' % (host.__unicode__()[0:25], extra)
        progress_info_s.send(sender=None, ptext=ptext, plen=ulen)
        for i, u in enumerate(updates):
            update = process_update(host, u, security)
            if update:
                host.updates.add(update)
            progress_update_s.send(sender=None, index=i + 1)


def parse_updates(updates_string):
    """ Parses updates string in a report and returns a sanitized version """

    updates = []
    ulist = updates_string.split()
    while ulist != []:
        updates.append('%s %s %s\n' % (ulist[0], ulist[1], ulist[2]))
        ulist.pop(0)
        ulist.pop(0)
        ulist.pop(0)

    return updates


@transaction.commit_manually
def process_update(host, update_string, security):
    """ Processes a single sanitized update string and converts to an update
    object
    """

    update_str = update_string.split()
    repo_id = update_str[2]

    parts = update_str[0].rpartition('.')
    package_str = parts[0]
    arch_str = parts[2]

    p_epoch, p_version, p_release = find_versions(update_str[1])

    package_arches = PackageArchitecture.objects.select_for_update()
    p_arch, c = package_arches.get_or_create(name=arch_str)
    transaction.commit()

    package_names = PackageName.objects.select_for_update()
    p_name, c = package_names.get_or_create(name=package_str)
    transaction.commit()

    packages = Package.objects.select_for_update()
    package, c = packages.get_or_create(name=p_name,
                                        arch=p_arch,
                                        epoch=p_epoch,
                                        version=p_version,
                                        release=p_release,
                                        packagetype='R')
    transaction.commit()

    try:
        repo = Repository.objects.get(repo_id=repo_id)
    except Repository.DoesNotExist:
        repo = None
    if repo:
        for mirror in repo.mirror_set.all():
            MirrorPackage.objects.create(mirror=mirror, package=package)
        transaction.commit()

    installed_package = host.packages.filter(name=p_name,
                                             arch=p_arch,
                                             packagetype='R')[0]

    updates = PackageUpdate.objects.select_for_update()
    update, c = updates.get_or_create(oldpackage=installed_package,
                                      newpackage=package,
                                      security=security)
    transaction.commit()
    return update


def parse_repos(repos_string):
    """ Parses repos string in a report and returns a sanitized version """

    repos = []
    for r in [s for s in repos_string.splitlines() if s]:
        repodata = re.findall('\'.*?\'', r)
        for i, rs in enumerate(repodata):
            repodata[i] = rs.replace('\'', '')
        repos.append(repodata)
    return repos


@transaction.commit_manually
def process_repo(repo, arch):
    """ Processes a single sanitized repo string and converts to a repo object
    """

    repository = r_id = None

    if repo[2] == '':
        r_priority = 0

    if repo[0] == 'deb':
        r_type = Repository.DEB
        r_priority = int(repo[2])
    elif repo[0] == 'rpm':
        r_type = Repository.RPM
        r_id = repo.pop(2)
        r_priority = int(repo[2]) * -1

    if repo[1]:
        r_name = repo[1]

    machine_arches = MachineArchitecture.objects.select_for_update()
    r_arch, c = machine_arches.get_or_create(name=arch)

    unknown = []
    for r_url in repo[3:]:
        try:
            mirror = Mirror.objects.get(url=r_url)
        except Mirror.DoesNotExist:
            if repository:
                Mirror.objects.create(repo=repository, url=r_url)
                transaction.commit()
            else:
                unknown.append(r_url)
        else:
            repository = mirror.repo
    if not repository:
        repositories = Repository.objects.select_for_update()
        repository, c = repositories.get_or_create(name=r_name,
                                                   arch=r_arch,
                                                   repotype=r_type)
        transaction.commit()
    if r_id:
        repository.repo_id = r_id

    for url in unknown:
        Mirror.objects.create(repo=repository, url=url)
    transaction.commit()

    for url_d in Mirror.objects.filter(repo=repository).values('url'):
        if url_d['url'].find('cdn.redhat.com') != -1 or \
                url_d['url'].find('nu.novell.com') != -1:
            repository.auth_required = True
    repository.save()
    transaction.commit()

    return repository, r_priority


def parse_packages(packages_string):
    """ Parses packages string in a report and returns a sanitized version """
    packages = []
    for p in packages_string.splitlines():
        packages.append(p.replace('\'', '').split(' '))
    return packages


@transaction.commit_manually
def process_package(pkg, protocol):
    """ Processes a single sanitized package string and converts to a package
        object """

    if protocol == '1':
        # ignore gpg-pupbkey pseudo packages
        if pkg[0] == 'gpg-pubkey':
            return
        try:
            name = pkg[0].lower()
            package_names = PackageName.objects.select_for_update()
            p_name, c = package_names.get_or_create(name=name)
            transaction.commit()
        except IntegrityError as e:
            print e
            p_name = package_names.get(name=name)
        except DatabaseError as e:
            print e
            transaction.rollback()

        if pkg[4] != '':
            arch = pkg[4]
        else:
            arch = 'unknown'
        package_arches = PackageArchitecture.objects.select_for_update()
        p_arch, c = package_arches.get_or_create(name=arch)

        p_epoch = p_version = p_release = ''

        if pkg[1]:
            p_epoch = pkg[1]
            if pkg[1] != '0':
                p_epoch = pkg[1]

        if pkg[2]:
            p_version = pkg[2]

        if pkg[3]:
            p_release = pkg[3]

        p_type = Package.UNKNOWN
        if pkg[5] == 'deb':
            p_type = Package.DEB
        if pkg[5] == 'rpm':
            p_type = Package.RPM

        try:
            packages = Package.objects.select_for_update()
            package, c = packages.get_or_create(name=p_name,
                                                arch=p_arch,
                                                epoch=p_epoch,
                                                version=p_version,
                                                release=p_release,
                                                packagetype=p_type)
            transaction.commit()
        except IntegrityError as e:
            print e
            package = packages.get(name=p_name,
                                   arch=p_arch,
                                   epoch=p_epoch,
                                   version=p_version,
                                   release=p_release,
                                   packagetype=p_type)
        except DatabaseError as e:
            print e
            transaction.rollback()
        return package
