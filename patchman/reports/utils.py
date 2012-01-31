# Copyright 2011 VPAC <furlongm@vpac.org>
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

from patchman.arch.models import MachineArchitecture, PackageArchitecture
from patchman.repos.models import Repository, Mirror
from patchman.packages.models import Package, PackageName
from patchman.signals import progress_info, progress_update


def process_repos(report, host):

    if report.repos:
        repos = parse_repos(report.repos)
        progress_info.send(sender=report, ptext='%s repos' % host.__unicode__()[0:25], plength=len(repos))
        for i, repo in enumerate(repos):
            repository = process_repo(report, repo)
            if repository:
                host.repos.add(repository)
            progress_update.send(sender=report, index=i + 1)


def process_packages(report, host):

    if report.packages:
        packages = parse_packages(report.packages)
        progress_info.send(sender=report, ptext='%s packages' % host.__unicode__()[0:25], plength=len(packages))
        for i, pkg in enumerate(packages):
            package = process_package(report, pkg)
            if package:
                host.packages.add(package)
            progress_update.send(sender=report, index=i + 1)


def parse_repos(repos_string):
    """Parses repo string in a report"""
    repos = []
    for r in repos_string.splitlines():
        repodata = re.findall('\'.*?\'', r)
        for i, rs in enumerate(repodata):
            repodata[i] = rs.replace('\'', '')
        repos.append(repodata)
    return repos


def process_repo(report, repo):
    if repo[0] == 'deb':
        r_type = Repository.DEB
    elif repo[0] == 'rpm':
        r_type = Repository.RPM
    r_name = repo[1]
    r_arch, c = MachineArchitecture.objects.get_or_create(name=report.arch)
    repository = None
    unknown = []
    for r_url in repo[2:]:
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
    for url in unknown:
        Mirror.objects.create(repo=repository, url=url)
    return repository


def parse_packages(packages_string):
    """Parses packages string in a report"""
    packages = []
    for p in packages_string.splitlines():
        packages.append(p.replace('\'', '').split(' '))
    return packages


def process_package(report, pkg):
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
