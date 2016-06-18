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

from __future__ import unicode_literals

from django.utils.encoding import python_2_unicode_compatible
from django.db import models, IntegrityError, DatabaseError, transaction
from django.db.models import Q
from django.utils import timezone

from rpm import labelCompare
from tagging.fields import TagField

from patchman.packages.models import Package, PackageUpdate
from patchman.domains.models import Domain
from patchman.repos.models import Repository
from patchman.operatingsystems.models import OS
from patchman.arch.models import MachineArchitecture
from patchman.signals import info_message, error_message
from patchman.hosts.utils import update_rdns, remove_reports


@python_2_unicode_compatible
class Host(models.Model):

    hostname = models.CharField(max_length=255, unique=True)
    ipaddress = models.GenericIPAddressField()
    reversedns = models.CharField(max_length=255, blank=True, null=True)
    check_dns = models.BooleanField(default=True)
    os = models.ForeignKey(OS)
    kernel = models.CharField(max_length=255)
    arch = models.ForeignKey(MachineArchitecture)
    domain = models.ForeignKey(Domain)
    lastreport = models.DateTimeField()
    packages = models.ManyToManyField(Package)
    repos = models.ManyToManyField(Repository, through='HostRepo')
    updates = models.ManyToManyField(PackageUpdate)
    reboot_required = models.BooleanField(default=False)
    host_repos_only = models.BooleanField(default=True)
    tags = TagField()
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta(object):
        verbose_name = 'Host'
        verbose_name_plural = 'Hosts'
        ordering = ('hostname',)

    def __str__(self):
        return self.hostname

    def show(self):
        """ Show info about this host
        """
        text = '{0!s}:\n'.format(self)
        text += 'IP address   : {0!s}\n'.format(self.ipaddress)
        text += 'Reverse DNS  : {0!s}\n'.format(self.reversedns)
        text += 'Domain       : {0!s}\n'.format(self.domain)
        text += 'OS           : {0!s}\n'.format(self.os)
        text += 'Kernel       : {0!s}\n'.format(self.kernel)
        text += 'Architecture : {0!s}\n'.format(self.arch)
        text += 'Last report  : {0!s}\n'.format(self.lastreport)
        text += 'Packages     : {0!s}\n'.format(self.get_num_packages())
        text += 'Repos        : {0!s}\n'.format(self.get_num_repos())
        text += 'Updates      : {0!s}\n'.format(self.get_num_updates())
        text += 'Tags         : {0!s}\n'.format(self.tags)
        text += 'Needs reboot : {0!s}\n'.format(self.reboot_required)
        text += 'Updated at   : {0!s}\n'.format(self.updated_at)
        text += 'Host repos   : {0!s}\n'.format(self.host_repos_only)

        info_message.send(sender=None, text=text)

    @models.permalink
    def get_absolute_url(self):
        return ('host_detail', [self.hostname])

    def get_num_security_updates(self):
        return self.updates.filter(security=True).count()

    def get_num_bugfix_updates(self):
        return self.updates.filter(security=False).count()

    def get_num_updates(self):
        return self.updates.count()

    def get_num_packages(self):
        return self.packages.count()

    def get_num_repos(self):
        return self.repos.count()

    def check_rdns(self):
        if self.check_dns:
            update_rdns(self)
            if self.hostname == self.reversedns:
                info_message.send(sender=None, text='Reverse DNS matches')
            else:
                text = 'Reverse DNS mismatch found:'
                text += '{0!s} != {1!s}'.format(self.hostname, self.reversedns)
                info_message.send(sender=None, text=text)
        else:
            info_message.send(sender=None,
                              text='Reverse DNS check disabled')

    def clean_reports(self, timestamp):
        remove_reports(self, timestamp)

    def get_host_repo_packages(self):
        if self.host_repos_only:
            hostrepos_q = Q(mirror__repo__in=self.repos.all(),
                            mirror__enabled=True, mirror__repo__enabled=True,
                            mirror__repo__hostrepo__enabled=True)
        else:
            hostrepos_q = \
                Q(mirror__repo__osgroup__os__host=self,
                  mirror__repo__arch=self.arch, mirror__enabled=True,
                  mirror__repo__enabled=True) | \
                Q(mirror__repo__in=self.repos.all(),
                  mirror__enabled=True, mirror__repo__enabled=True)
        return Package.objects.select_related().filter(hostrepos_q).distinct()

    def process_update(self, package, highest_package):
        if self.host_repos_only:
            host_repos = Q(repo__host=self)
        else:
            host_repos = \
                Q(repo__osgroup__os__host=self, repo__arch=self.arch) | \
                Q(repo__host=self)
        mirrors = highest_package.mirror_set.filter(host_repos)
        security = False
        # If any of the containing repos are security,
        # mark the update as security
        for mirror in mirrors:
            if mirror.repo.security:
                security = True
        try:
            updates = PackageUpdate.objects.all()
            with transaction.atomic():
                update, c = updates.get_or_create(
                    oldpackage=package,
                    newpackage=highest_package,
                    security=security)
        except IntegrityError as e:
            error_message.send(sender=None, text=e)
            update = updates.get(oldpackage=package,
                                 newpackage=highest_package,
                                 security=security)
        except DatabaseError as e:
            error_message.send(sender=None, text=e)
        try:
            with transaction.atomic():
                self.updates.add(update)
            info_message.send(sender=None, text='{0!s}'.format(update))
            return update.id
        except IntegrityError as e:
            error_message.send(sender=None, text=e)
        except DatabaseError as e:
            error_message.send(sender=None, text=e)

    def find_updates(self):

        old_updates = self.updates.all()

        kernels_q = Q(name__name='kernel') | Q(name__name='kernel-devel') | \
            Q(name__name='kernel-pae') | Q(name__name='kernel-pae-devel') | \
            Q(name__name='kernel-xen') | Q(name__name='kernel-xen-devel') | \
            Q(name__name='kernel-headers') | Q(name__name='kernel-default')
        repo_packages = self.get_host_repo_packages()
        host_packages = self.packages.exclude(kernels_q).distinct()
        kernel_packages = self.packages.filter(kernels_q)

        if self.host_repos_only:
            update_ids = self.find_host_repo_updates(host_packages,
                                                     repo_packages)
        else:
            update_ids = self.find_osgroup_repo_updates(host_packages,
                                                        repo_packages)

        kernel_update_ids = self.find_kernel_updates(kernel_packages,
                                                     repo_packages)
        for ku_id in kernel_update_ids:
            update_ids.append(ku_id)

        removals = old_updates.exclude(pk__in=update_ids)
        for update in removals:
            self.updates.remove(update)

    def find_best_repo(self, package, hostrepos):

        best_repo = None
        package_repos = hostrepos.filter(repo__mirror__packages=package)

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

    def find_host_repo_updates(self, host_packages, repo_packages):

        update_ids = []
        hostrepos_q = Q(repo__mirror__enabled=True,
                        repo__mirror__repo__enabled=True, host=self)
        hostrepos = HostRepo.objects.select_related().filter(hostrepos_q)

        for package in host_packages:
            highest_package = package
            best_repo = self.find_best_repo(package, hostrepos)
            priority = None
            if best_repo is not None:
                priority = best_repo.priority

            # find the packages that are potential updates
            pu_q = Q(name=package.name, arch=package.arch,
                     packagetype=package.packagetype)
            potential_updates = repo_packages.filter(pu_q)
            for potential_update in potential_updates:

                if highest_package.compare_version(potential_update) == -1 \
                        and package.compare_version(potential_update) == -1:

                    if priority is not None:
                        # proceed only if the package is from a repo with a
                        # priority and that priority is >= the repo priority
                        pu_best_repo = self.find_best_repo(potential_update,
                                                           hostrepos)
                        pu_priority = pu_best_repo.priority
                        if priority >= pu_priority:
                            highest_package = potential_update
                    else:
                        highest_package = potential_update

            if highest_package != package:
                uid = self.process_update(package, highest_package)
                if uid is not None:
                    update_ids.append(uid)

        return update_ids

    def find_osgroup_repo_updates(self, host_packages, repo_packages):

        update_ids = []

        for package in host_packages:
            highest_package = package

            # find the packages that are potential updates
            pu_q = Q(name=package.name, arch=package.arch,
                     packagetype=package.packagetype)
            potential_updates = repo_packages.filter(pu_q)
            for potential_update in potential_updates:

                if highest_package.compare_version(potential_update) == -1 \
                        and package.compare_version(potential_update) == -1:
                    highest_package = potential_update

            if highest_package != package:
                uid = self.process_update(package, highest_package)
                if uid is not None:
                    update_ids.append(uid)

        return update_ids

    def check_if_reboot_required(self, host_highest):

        to_strip = ['xen', '-xen', 'PAE', '-pae', '-default', 'vanilla', '-pv']
        kernel = self.kernel
        for s in to_strip:
            if kernel.endswith(s):
                kernel = kernel[:-len(s)]
        ver, rel = kernel.rsplit('-')
        kernel_ver = ('', str(ver), str(rel))
        host_highest_ver = ('', host_highest.version, host_highest.release)
        if labelCompare(kernel_ver, host_highest_ver) == -1:
            self.reboot_required = True
        else:
            self.reboot_required = False

    def find_kernel_updates(self, kernel_packages, repo_packages):

        update_ids = []

        for package in kernel_packages:
            host_highest = package
            repo_highest = package

            pk_q = Q(name=package.name)
            potential_updates = repo_packages.filter(pk_q)
            for pu in potential_updates:
                if package.compare_version(pu) == -1 \
                        and repo_highest.compare_version(pu) == -1:
                    repo_highest = pu

            host_packages = self.packages.filter(pk_q)
            for hp in host_packages:
                if package.compare_version(hp) == -1 and \
                        host_highest.compare_version(hp) == -1:
                    host_highest = hp

            if host_highest.compare_version(repo_highest) == -1:
                uid = self.process_update(host_highest, repo_highest)
                if uid is not None:
                    update_ids.append(uid)

            self.check_if_reboot_required(host_highest)

        try:
            with transaction.atomic():
                self.save()
        except DatabaseError as e:
            error_message.send(sender=None, text=e)

        return update_ids


@python_2_unicode_compatible
class HostRepo(models.Model):
    host = models.ForeignKey(Host)
    repo = models.ForeignKey(Repository)
    enabled = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)

    class Meta(object):
        unique_together = ('host', 'repo')

    def __str__(self):
        return '{0!s}-{1!s}'.format(self.host, self.repo)
