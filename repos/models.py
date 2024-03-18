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

from django.db import models
from django.urls import reverse

from arch.models import MachineArchitecture
from packages.models import Package
from util import get_setting_of_type

from repos.repo_types.deb import refresh_deb_repo
from repos.repo_types.rpm import refresh_rpm_repo, refresh_repo_errata
from repos.repo_types.arch import refresh_arch_repo
from repos.repo_types.gentoo import refresh_gentoo_repo
from patchman.signals import info_message, warning_message, error_message


class Repository(models.Model):

    RPM = 'R'
    DEB = 'D'
    ARCH = 'A'
    GENTOO = 'G'

    REPO_TYPES = (
        (RPM, 'rpm'),
        (DEB, 'deb'),
        (ARCH, 'arch'),
        (GENTOO, 'gentoo')
    )

    name = models.CharField(max_length=255, unique=True)
    arch = models.ForeignKey(MachineArchitecture, on_delete=models.CASCADE)
    security = models.BooleanField(default=False)
    repotype = models.CharField(max_length=1, choices=REPO_TYPES)
    enabled = models.BooleanField(default=True)
    repo_id = models.CharField(max_length=255, null=True, blank=True)
    auth_required = models.BooleanField(default=False)

    from repos.managers import RepositoryManager
    objects = RepositoryManager()

    class Meta:
        verbose_name = 'Repository'
        verbose_name_plural = 'Repositories'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('repos:repo_detail', args=[str(self.id)])

    def show(self):
        """ Show info about this repo, including mirrors
        """
        text = f'{self.id} : {self.name}\n'
        text += f'security: {self.security}    '
        text += f'arch: {self.arch}\n'
        text += 'Mirrors:'

        info_message.send(sender=None, text=text)

        for mirror in self.mirror_set.all():
            mirror.show()

    def refresh(self, force=False):
        """ Refresh all of a repos mirror metadata,
            force can be set to force a reset of all the mirrors metadata
        """
        if force:
            for mirror in self.mirror_set.all():
                mirror.packages_checksum = None
                mirror.modules_checksum = None
                mirror.errata_checksum = None
                mirror.save()

        if not self.auth_required:
            if self.repotype == Repository.DEB:
                refresh_deb_repo(self)
            elif self.repotype == Repository.RPM:
                refresh_rpm_repo(self)
            elif self.repotype == Repository.ARCH:
                refresh_arch_repo(self)
            elif self.repotype == Repository.GENTOO:
                refresh_gentoo_repo(self)
            else:
                text = f'Error: unknown repo type for repo {self.id}: {self.repotype}'
                error_message.send(sender=None, text=text)
        else:
            text = 'Repo requires authentication, not updating'
            warning_message.send(sender=None, text=text)

    def refresh_errata(self, force=False):
        """ Refresh errata metadata for all of a repos mirrors
        """
        if force:
            for mirror in self.mirror_set.all():
                mirror.errata_checksum = None
                mirror.save()
        if self.repotype == Repository.RPM:
            refresh_repo_errata(self)

    def disable(self):
        """ Disable a repo. This involves disabling each mirror, which stops it
            being considered for package updates, and disabling refresh for
            each mirror so that it doesn't try to update its package metadata.
        """
        self.enabled = False
        for mirror in self.mirror_set.all():
            mirror.enabled = False
            mirror.refresh = False
            mirror.save()

    def enable(self):
        """ Enable a repo. This involves enabling each mirror, which allows it
            to be considered for package updates, and enabling refresh for each
            mirror so that it updates its package metadata.
        """
        self.enabled = True
        for mirror in self.mirror_set.all():
            mirror.enabled = True
            mirror.refresh = True
            mirror.save()


class Mirror(models.Model):

    repo = models.ForeignKey(Repository, on_delete=models.CASCADE)
    url = models.CharField(max_length=255, unique=True)
    last_access_ok = models.BooleanField(default=False)
    packages_checksum = models.CharField(max_length=255, blank=True, null=True)
    modules_checksum = models.CharField(max_length=255, blank=True, null=True)
    errata_checksum = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    packages = models.ManyToManyField(Package, blank=True, through='MirrorPackage')
    mirrorlist = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    refresh = models.BooleanField(default=True)
    fail_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Mirror'
        verbose_name_plural = 'Mirrors'

    def __str__(self):
        return self.url

    def get_absolute_url(self):
        return reverse('repos:mirror_detail', args=[str(self.id)])

    def show(self):
        """ Show info about this mirror
        """
        text = f' {self.id} : {self.url}\n'
        text += ' last updated: '
        text += f'{self.timestamp}    checksum: {self.packages_checksum}\n'
        info_message.send(sender=None, text=text)

    def fail(self):
        """ Records that the mirror has failed
            Disables refresh on a mirror if it fails more than MAX_MIRROR_FAILURES times
            Set MAX_MIRROR_FAILURES to -1 to disable marking mirrors as failures
            Default is 28
        """
        if self.repo.auth_required:
            text = f'Mirror requires authentication, not updating - {self.url}'
            warning_message.send(sender=None, text=text)
            return
        text = f'No usable mirror found at {self.url}'
        error_message.send(sender=None, text=text)
        default_max_mirror_failures = 28
        max_mirror_failures = get_setting_of_type(
            setting_name='MAX_MIRROR_FAILURES',
            setting_type=int,
            default=default_max_mirror_failures
        )
        self.fail_count = self.fail_count + 1
        if max_mirror_failures == -1:
            text = f'Mirror has failed {self.fail_count} times, but MAX_MIRROR_FAILURES=-1, not disabling refresh'
            error_message.send(sender=None, text=text)
        elif self.fail_count > max_mirror_failures:
            self.refresh = False
            text = f'Mirror has failed {self.fail_count} times (max={max_mirror_failures}), disabling refresh'
            error_message.send(sender=None, text=text)
        self.last_access_ok = False
        self.save()


class MirrorPackage(models.Model):
    mirror = models.ForeignKey(Mirror, on_delete=models.CASCADE)
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    enabled = models.BooleanField(default=True)
