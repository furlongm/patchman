
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

from django.db import models
from django.db.models import Q, Count

from rpm import labelCompare
from debian.debian_support import Version, version_compare
from tagging.fields import TagField

from patchman.packages.models import Package, PackageUpdate
from patchman.domains.models import Domain
from patchman.repos.models import Repository
from patchman.operatingsystems.models import OS
from patchman.arch.models import MachineArchitecture
from patchman.hosts.signals import host_update_found


class Host(models.Model):

    hostname = models.CharField(max_length=255, unique=True)
    ipaddress = models.IPAddressField()
    os = models.ForeignKey(OS)
    kernel = models.CharField(max_length=255)
    arch = models.ForeignKey(MachineArchitecture)
    domain = models.ForeignKey(Domain)
    lastreport = models.DateTimeField()
    packages = models.ManyToManyField(Package)
    repos = models.ManyToManyField(Repository, through='HostRepo')
    updates = models.ManyToManyField(PackageUpdate)
    reboot_required = models.BooleanField(default=False)
    host_repos_only = models.BooleanField(default=False)
    tags = TagField()

    class Meta:
        ordering = ('hostname',)

    def __unicode__(self):
        return self.hostname

    @models.permalink
    def get_absolute_url(self):
        return ('host_detail', [self.hostname])

    def sec_count(self):
        return self.updates.filter(security=True).count()

    def nonsec_count(self):
        return self.updates.filter(security=False).count()

    def get_host_repo_packages(self):
        # FIXME: add support for host repos being enabled/disabled via the 'through' field
        if self.host_repos_only:
            hostrepos = Q(mirror__repo__in=self.repos.all(), mirror__enabled=True, mirror__repo_enabled=True)
        else:
            hostrepos = Q(mirror__repo__osgroup__os__host=self, mirror__repo__arch=self.arch, mirror__enabled=True, mirror__repo_enabled=True) | Q(mirror__repo__in=self.repos.all(), mirror__enabled=True, mirror__repo__enabled=True)
        return Package.objects.select_related().filter(hostrepos)

    def find_updates(self):

        self.updates.clear()

        kernels = Q(name__name='kernel') | Q(name__name='kernel-xen') | Q(name__name='kernel-pae') | Q(name__name='kernel-devel') | Q(name__name='kernel-pae-devel') | Q(name__name='kernel-xen-devel') | Q(name__name='kernel-headers')
        kernelpackages = Package.objects.select_related().filter(host=self).filter(kernels).values('name__name').annotate(Count('name'))

        repopackages = self.get_host_repo_packages()

        for package in self.packages.exclude(kernels):
            highest = ('', '0', '')
            highestpackage = None
            matchingpackages = repopackages.filter(name=package.name, arch=package.arch, packagetype=package.packagetype)
            for repopackage in matchingpackages:
                if package.compare_version(repopackage) == -1:
                    if package.packagetype == 'R':
                        if labelCompare(highest, repopackage._version_string_rpm()) == -1:
                            highest = repopackage._version_string_rpm()
                            highestpackage = repopackage
                    elif package.packagetype == 'D':
                        vr = Version(repopackage._version_string_deb())
                        if highest == ('', '0', ''):
                            vh = Version('0')
                        else:
                            vh = Version('%s:%s-%s' % (str(highest[0]), str(highest[1]), str(highest[2])))
                        if version_compare(vh, vr) == -1:
                            highest = repopackage._version_string_deb()
                            highestpackage = repopackage

            if highest != ('', '0', ''):
                hostrepos = Q(repo__osgroup__os__host=self, repo__arch=self.arch) | Q(repo__host=self)
                matchingrepos = highestpackage.mirror_set.filter(hostrepos)
                security = False
                # If any of the containing repos are security, mark the update as security
                for mirror in matchingrepos:
                    if mirror.repo.security == True:
                        security = True
                update, c = PackageUpdate.objects.get_or_create(oldpackage=package, newpackage=highestpackage, security=security)
                self.updates.add(update)
                host_update_found.send(sender=self, update=update)

        try:
            ver, rel = self.kernel.rsplit('-')
            rel = rel.rstrip('xen')
            rel = rel.rstrip('PAE')
            running_kernel = ('', str(ver), str(rel))
            for package in kernelpackages:
                host_highest = ('', '', '')
                repo_highest = ('', '', '')
                host_highest_package = None
                repo_highest_package = None
                matchingpackages = repopackages.filter(Q(name__name=package['name__name']))
                for repopackage in matchingpackages:
                    repokernel = repopackage._version_string_rpm()
                    if labelCompare(repo_highest, repokernel) == -1:
                        repo_highest = repokernel
                        repo_highest_package = repopackage
                matchingpackages = self.packages.filter(Q(name__name=package['name__name']))
                for hostpackage in matchingpackages:
                    hostkernel = hostpackage._version_string_rpm()
                    if labelCompare(host_highest, hostkernel) == -1:
                        host_highest = hostkernel
                        host_highest_package = hostpackage
                if labelCompare(host_highest, repo_highest) == -1:
                    matchingrepos = repo_highest_package.mirror_set.filter(repo__arch=self.arch)
                    security = False
                    # If any of the containing repos are security, mark the update as security
                    for mirror in matchingrepos:
                        if mirror.repo.security == True:
                            security = True
                    update, c = PackageUpdate.objects.get_or_create(oldpackage=host_highest_package, newpackage=repo_highest_package, security=security)
                    self.updates.add(update)
                    host_update_found.send(sender=self, update=update)
                if labelCompare(running_kernel, host_highest) == -1:
                    self.reboot_required = True
                else:
                    self.reboot_required = False
        except ValueError:  # debian kernel
            pass
        self.save()


class HostRepo(models.Model):
    host = models.ForeignKey(Host)
    repo = models.ForeignKey(Repository)
    enabled = models.BooleanField(default=True)
