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

from patchman.hosts.models import HostRepo
from patchman.arch.models import MachineArchitecture, PackageArchitecture
from patchman.repos.models import Repository, Mirror, MirrorPackage
from patchman.packages.models import Package, PackageName, PackageUpdate
from patchman.packages.utils import find_versions
from patchman.signals import progress_info_s, progress_update_s


def process_repos(report, host):
    """ Processes the quoted repos string sent with a report """

    if report.repos:
        repos = parse_repos(report.repos)
        progress_info_s.send(sender=None, ptext='%s repos' % host.__unicode__()[0:25], plen=len(repos))
        for i, repo in enumerate(repos):
            repository, priority = process_repo(report, repo)
            if repository:
                hostrepo, c = HostRepo.objects.get_or_create(host=host, repo=repository, priority=priority, enabled=True)
                hostrepo.save()
            progress_update_s.send(sender=None, index=i + 1)


def process_packages(report, host):
    """ Processes the quoted packages string sent with a report """

    if report.packages:
        packages = parse_packages(report.packages)
        progress_info_s.send(sender=None, ptext='%s packages' % host.__unicode__()[0:25], plen=len(packages))
        for i, pkg in enumerate(packages):
            package = process_package(report, pkg)
            if package:
                host.packages.add(package)
            progress_update_s.send(sender=None, index=i + 1)


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
        progress_info_s.send(sender=None, ptext='%s %s updates' % (host.__unicode__()[0:25], extra), plen=ulen)
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


def process_update(host, update_string, security):
    """ Processes a single sanitized update string and converts to an update object """

    update_l = update_string.split()
    parts = update_l[0].rpartition('.')
    p_str = parts[0]
    a_str = parts[2]
    p_epoch, p_ver, p_rel = find_versions(update_l[1])
    repo_id = update_l[2]

    p_arch, c = PackageArchitecture.objects.get_or_create(name=a_str)
    p_name, c = PackageName.objects.get_or_create(name=p_str)
    package, c = Package.objects.get_or_create(name=p_name, arch=p_arch, epoch=p_epoch, version=p_ver, release=p_rel, packagetype='R')

    repo = Repository.objects.get(repo_id=repo_id)
    if repo:
        for mirror in repo.mirror_set.all():
            MirrorPackage.objects.create(mirror=mirror, package=package)

    hp = host.packages.filter(name=p_name, arch=p_arch, packagetype='R')[0]

    update, c = PackageUpdate.objects.get_or_create(oldpackage=hp, newpackage=package, security=security)

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


def process_repo(report, repo):
    """ Processes a single sanitized repo string and converts to a repo object """
    if repo[2] == '':
        r_priority = 0
    if repo[0] == 'deb':
        r_type = Repository.DEB
        r_priority = int(repo[2])
    elif repo[0] == 'rpm':
        r_type = Repository.RPM
        r_id = repo.pop(2)
        r_priority = int(repo[2]) * -1
    r_name = repo[1]
    r_arch, c = MachineArchitecture.objects.get_or_create(name=report.arch)
    repository = None
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
        repository, c = Repository.objects.get_or_create(name=r_name, arch=r_arch, repotype=r_type)
    if r_id:
        repository.repo_id = r_id
    for url in unknown:
        Mirror.objects.create(repo=repository, url=url)
    for url_d in Mirror.objects.filter(repo=repository).values('url'):
        if url_d['url'].find('cdn.redhat.com') != -1:
            repository.auth_required = True
    repository.save()
    return repository, r_priority


def parse_packages(packages_string):
    """ Parses packages string in a report and returns a sanitized version """
    packages = []
    for p in packages_string.splitlines():
        packages.append(p.replace('\'', '').split(' '))
    return packages


def process_package(report, pkg):
    """ Processes a single sanitized package string and converts to a package object """
    if report.protocol == '1':
        if pkg[0] != 'gpg-pubkey':
            p_name, c = PackageName.objects.get_or_create(name=pkg[0].lower())
        else:
            return None
        if pkg[4] != '':
            p_arch, c = PackageArchitecture.objects.get_or_create(name=pkg[4])
        else:
            p_arch, c = PackageArchitecture.objects.get_or_create(name='unknown')
        if pkg[1]:
            p_epoch = pkg[1]
            if p_epoch == '0':
                p_epoch = ''
        else:
            p_epoch = ''
        p_version = pkg[2]
        if pkg[3]:
            p_release = pkg[3]
        else:
            p_release = ''
        p_type = Package.UNKNOWN
        if pkg[5] == 'deb':
            p_type = Package.DEB
        if pkg[5] == 'rpm':
            p_type = Package.RPM
        package, c = Package.objects.get_or_create(name=p_name, arch=p_arch, epoch=p_epoch, version=p_version, release=p_release, packagetype=p_type)
        return package
