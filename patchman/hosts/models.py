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

from django.db import models, IntegrityError, DatabaseError, transaction
from django.db.models import Q, Count

from rpm import labelCompare
from debian.debian_support import Version, version_compare
from tagging.fields import TagField
from datetime import datetime

from packages.models import Package, PackageUpdate
from domains.models import Domain
from repos.models import Repository
from operatingsystems.models import OS
from arch.models import MachineArchitecture
from signals import info_message
from hosts.utils import update_rdns, remove_reports


class Host(models.Model):

    hostname = models.CharField(max_length=255, unique=True)
    ipaddress = models.IPAddressField()
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
    updated_at = models.DateTimeField(default=datetime.now())

    class Meta:
        ordering = ('hostname',)

    def __unicode__(self):
        return self.hostname

    def show(self):
        """ Show info about this host
        """
        text = []
        text.append('%s:\n' % self)
        text.append('IP address   : %s\n' % self.ipaddress)
        text.append('Reverse DNS  : %s\n' % self.reversedns)
        text.append('Domain       : %s\n' % self.domain)
        text.append('OS           : %s\n' % self.os)
        text.append('Kernel       : %s\n' % self.kernel)
        text.append('Architecture : %s\n' % self.arch)
        text.append('Last report  : %s\n' % self.lastreport)
        text.append('Packages     : %s\n' % self.get_num_packages())
        text.append('Repos        : %s\n' % self.get_num_repos())
        text.append('Updates      : %s\n' % self.get_num_updates())
        text.append('Tags         : %s\n' % self.tags)
        text.append('Needs reboot : %s\n' % self.reboot_required)
        text.append('Updated at   : %s\n' % self.updated_at)
        text.append('Host repos   : %s\n' % self.host_repos_only)
        text.append('\n')

        for line in text:
            info_message.send(sender=None, text=line)

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
                info_message.send(sender=None, text='Reverse DNS matches\n')
            else:
                info_message.send(sender=None,
                                  text='Reverse DNS mismatch found: %s != %s\n'
                                  % (self.hostname, self.reversedns))
        else:
            info_message.send(sender=None,
                              text='Reverse DNS check disabled\n')

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

    @transaction.commit_manually
    def process_update(self, package, highest_ver, highest_package):
        if highest_ver != ('', '0', ''):
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
                updates = PackageUpdate.objects.select_for_update()
                update, c = updates.get_or_create(oldpackage=package,
                                                  newpackage=highest_package,
                                                  security=security)
                transaction.commit()
            except IntegrityError as e:
                print e
                update = updates.get(oldpackage=package,
                                     newpackage=highest_package,
                                     security=security)
            except DatabaseError as e:
                print e
                transaction.rollback()
            try:
                self.updates.add(update)
                info_message.send(sender=None, text="%s\n" % update)
                transaction.commit()
                return update.id
            except IntegrityError as e:
                print e
            except DatabaseError as e:
                print e
                transaction.rollback()
        transaction.commit()

    @transaction.commit_manually
    def find_updates(self):

        old_updates = self.updates.all()

        kernels_q = Q(name__name='kernel') | Q(name__name='kernel-devel') | \
            Q(name__name='kernel-pae') | Q(name__name='kernel-pae-devel') | \
            Q(name__name='kernel-xen') | Q(name__name='kernel-xen-devel') | \
            Q(name__name='kernel-headers')
        repo_packages = self.get_host_repo_packages()
        host_packages = self.packages.exclude(kernels_q).distinct()
        kernels = self.packages.filter(kernels_q)
        kernel_packages = kernels.values('name__name').annotate(Count('name'))
        transaction.commit()

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
        transaction.commit()

    def find_best_repo(self, package, hostrepos):

        best_repo = None
        package_repos = hostrepos.filter(repo__mirror__packages__name=package)

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

    def find_highest_ver(self, package_type, potential_update,
                         highest_ver, highest_package):

        if package_type == 'R':
            pu_ver = potential_update._version_string_rpm()
            if labelCompare(highest_ver, pu_ver) == -1:
                highest_ver = pu_ver
                highest_package = potential_update

        elif package_type == 'D':
            pu_ver = potential_update._version_string_deb()
            pu_deb_ver = Version(pu_ver)
            if highest_ver == ('', '0', ''):
                highest_deb_ver = Version('0')
            else:
                ver_str = '%s:%s-%s' % (str(highest_ver[0]),
                                        str(highest_ver[1]),
                                        str(highest_ver[2]))
                highest_deb_ver = Version(ver_str)
            if version_compare(highest_deb_ver, pu_deb_ver) == -1:
                highest_ver = pu_ver
                highest_package = potential_update

        return highest_ver, highest_package

    def find_host_repo_updates(self, host_packages, repo_packages):

        update_ids = []

        hostrepos_q = Q(repo__mirror__enabled=True,
                        repo__mirror__repo__enabled=True, host=self)
        hostrepos = HostRepo.objects.select_related().filter(hostrepos_q)

        for package in host_packages:
            highest_ver = ('', '0', '')
            highest_package = None

            best_repo = self.find_best_repo(package.name, hostrepos)

            # find the packages that are potential updates
            pu_q = Q(name=package.name, arch=package.arch,
                     packagetype=package.packagetype)
            potential_updates = repo_packages.filter(pu_q)
            for potential_update in potential_updates:

                if package.compare_version(potential_update) == -1:

                    pu_best_repo = self.find_best_repo(potential_update.name,
                                                       hostrepos)
                    priority = pu_best_repo.priority

                    # proceed if that repo has a higher priority
                    if priority >= best_repo.priority:
                        highest_ver, highest_package = \
                            self.find_highest_ver(package.packagetype,
                                                  potential_update,
                                                  highest_ver, highest_package)

            uid = self.process_update(package, highest_ver, highest_package)
            if uid is not None:
                update_ids.append(uid)

        return update_ids

    def find_osgroup_repo_updates(self, host_packages, repo_packages):

        update_ids = []

        for package in host_packages:
            highest_ver = ('', '0', '')
            highest_package = None

            # find the packages that are potential updates
            pu_q = Q(name=package.name, arch=package.arch,
                     packagetype=package.packagetype)
            potential_updates = repo_packages.filter(pu_q)
            for potential_update in potential_updates:

                if package.compare_version(potential_update) == -1:

                    highest_ver, highest_package = \
                        self.find_highest_ver(package.packagetype,
                                              potential_update,
                                              highest_ver, highest_package)

            uid = self.process_update(package, highest_ver, highest_package)
            if uid is not None:
                update_ids.append(uid)

        return update_ids

    def check_if_reboot_required(self, running_kernel_ver, host_highest_ver):
        if labelCompare(running_kernel_ver, host_highest_ver) == -1:
            self.reboot_required = True
        else:
            self.reboot_required = False

    @transaction.commit_manually
    def find_kernel_updates(self, kernel_packages, repo_packages):

        update_ids = []

        try:
            ver, rel = self.kernel.rsplit('-')
            rel = rel.rstrip('xen')
            rel = rel.rstrip('PAE')
            kernel_ver = ('', str(ver), str(rel))

            for package in kernel_packages:
                host_highest_ver = ('', '', '')
                repo_highest_ver = ('', '', '')
                host_highest_package = None
                repo_highest_package = None
                pk_q = Q(name__name=package['name__name'])

                potential_kernels = repo_packages.filter(pk_q)
                for potential_kernel in potential_kernels:
                    repo_highest_ver, repo_highest_package = \
                        self.find_highest_ver('R', potential_kernel,
                                              repo_highest_ver,
                                              repo_highest_package)

                host_kernels = self.packages.filter(pk_q)
                for host_kernel in host_kernels:
                    host_highest_ver, host_highest_package = \
                        self.find_highest_ver('R', potential_kernel,
                                              host_highest_ver,
                                              host_highest_package)

                if labelCompare(host_highest_ver, repo_highest_ver) == -1:
                    uid = self.process_update(host_highest_package,
                                              repo_highest_ver,
                                              repo_highest_package)
                    if uid is not None:
                        update_ids.append(uid)

                self.check_if_reboot_required(kernel_ver, host_highest_ver)

        except ValueError:  # debian kernel
            pass
        try:
            self.save()
            transaction.commit()
        except DatabaseError as e:
            print e
            transaction.rollback()

        return update_ids


class HostRepo(models.Model):
    host = models.ForeignKey(Host)
    repo = models.ForeignKey(Repository)
    enabled = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)

    class Meta:
        unique_together = ('host', 'repo')

    def __unicode__(self):
        return '%s-%s' % (self.host, self.repo)
