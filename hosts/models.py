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

from django.db import models, IntegrityError, DatabaseError, transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

try:
    from version_utils.rpm import labelCompare
except ImportError:
    from rpm import labelCompare
from tagging.fields import TagField

from packages.models import Package, PackageUpdate
from domains.models import Domain
from repos.models import Repository
from operatingsystems.models import OS
from arch.models import MachineArchitecture
from patchman.signals import info_message, error_message
from repos.utils import find_best_repo
from hosts.utils import update_rdns, remove_reports


class Host(models.Model):

    hostname = models.CharField(max_length=255, unique=True)
    ipaddress = models.GenericIPAddressField()
    reversedns = models.CharField(max_length=255, blank=True, null=True)
    check_dns = models.BooleanField(default=False)
    os = models.ForeignKey(OS, on_delete=models.CASCADE)
    kernel = models.CharField(max_length=255)
    arch = models.ForeignKey(MachineArchitecture, on_delete=models.CASCADE)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    lastreport = models.DateTimeField()
    packages = models.ManyToManyField(Package, blank=True)
    repos = models.ManyToManyField(Repository, blank=True, through='HostRepo')
    updates = models.ManyToManyField(PackageUpdate, blank=True)
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

    def get_absolute_url(self):
        return reverse('hosts:host_detail', args=[self.hostname])

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
            if self.hostname.lower() == self.reversedns.lower():
                info_message.send(sender=None, text='Reverse DNS matches')
            else:
                text = 'Reverse DNS mismatch found: '
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
        updates = PackageUpdate.objects.all()
        # see if any version of this update exists
        # if it's already marked as a security update, leave it that way
        # if not, mark it as a security update
        # this could be an issue if different distros mark the same update
        # in different ways (security vs bugfix) but in reality this is not
        # very likely to happen. if it does, we err on the side of caution
        # and mark it as the security update
        try:
            update = updates.get(
                oldpackage=package,
                newpackage=highest_package
            )
        except PackageUpdate.DoesNotExist:
            update = None
        try:
            if update:
                if security and not update.security:
                    update.security = True
                    with transaction.atomic():
                        update.save()
            else:
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

        kernels_q = Q(name__name='kernel') | \
            Q(name__name='kernel-devel') | \
            Q(name__name='kernel-preempt') | \
            Q(name__name='kernel-preempt-devel') | \
            Q(name__name='kernel-rt') | \
            Q(name__name='kernel-rt-devel') | \
            Q(name__name='kernel-debug') | \
            Q(name__name='kernel-debug-devel') | \
            Q(name__name='kernel-default') | \
            Q(name__name='kernel-default-devel') | \
            Q(name__name='kernel-headers') | \
            Q(name__name='kernel-core') | \
            Q(name__name='kernel-modules') | \
            Q(name__name='virtualbox-kmp-default') | \
            Q(name__name='virtualbox-kmp-preempt') | \
            Q(name__name='kernel-uek') | \
            Q(name__name='kernel-uek-devel') | \
            Q(name__name='kernel-uek-debug') | \
            Q(name__name='kernel-uek-debug-devel') | \
            Q(name__name='kernel-uek-container') | \
            Q(name__name='kernel-uek-container-debug') | \
            Q(name__name='kernel-uek-doc')
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

        for update in self.updates.all():
            if update.id not in update_ids:
                self.updates.remove(update)

    def find_host_repo_updates(self, host_packages, repo_packages):

        update_ids = []
        hostrepos_q = Q(repo__mirror__enabled=True,
                        repo__mirror__refresh=True,
                        repo__mirror__repo__enabled=True,
                        host=self)
        hostrepos = HostRepo.objects.select_related().filter(hostrepos_q)

        for package in host_packages:
            highest_package = package
            best_repo = find_best_repo(package, hostrepos)
            priority = None
            if best_repo is not None:
                priority = best_repo.priority

            # find the packages that are potential updates
            pu_q = Q(name=package.name, arch=package.arch,
                     packagetype=package.packagetype)
            potential_updates = repo_packages.filter(pu_q)
            for pu in potential_updates:
                if highest_package.compare_version(pu) == -1 \
                        and package.compare_version(pu) == -1:

                    if priority is not None:
                        # proceed only if the package is from a repo with a
                        # priority and that priority is >= the repo priority
                        pu_best_repo = find_best_repo(pu, hostrepos)
                        pu_priority = pu_best_repo.priority
                        if pu_priority >= priority:
                            highest_package = pu
                    else:
                        highest_package = pu

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
            for pu in potential_updates:
                if highest_package.compare_version(pu) == -1 \
                        and package.compare_version(pu) == -1:
                    highest_package = pu

            if highest_package != package:
                uid = self.process_update(package, highest_package)
                if uid is not None:
                    update_ids.append(uid)

        return update_ids

    def check_if_reboot_required(self, host_highest):

        ver, rel = self.kernel.split('-')[:2]
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

            pu_q = Q(name=package.name)
            potential_updates = repo_packages.filter(pu_q)
            for pu in potential_updates:
                if package.compare_version(pu) == -1 \
                        and repo_highest.compare_version(pu) == -1:
                    repo_highest = pu

            host_packages = self.packages.filter(pu_q)
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


class HostRepo(models.Model):
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    repo = models.ForeignKey(Repository, on_delete=models.CASCADE)
    enabled = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)

    class Meta(object):
        unique_together = ('host', 'repo')

    def __str__(self):
        return '{0!s}-{1!s}'.format(self.host, self.repo)
