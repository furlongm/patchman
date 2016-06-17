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

from django.db import models

from patchman.arch.models import MachineArchitecture
from patchman.packages.models import Package

from patchman.repos.utils import refresh_deb_repo, refresh_rpm_repo, \
    update_mirror_packages
from patchman.signals import info_message, warning_message, error_message


class Repository(models.Model):

    RPM = 'R'
    DEB = 'D'

    REPO_TYPES = (
        (RPM, 'rpm'),
        (DEB, 'deb'),
    )

    name = models.CharField(max_length=255, unique=True)
    arch = models.ForeignKey(MachineArchitecture)
    security = models.BooleanField(default=False)
    repotype = models.CharField(max_length=1, choices=REPO_TYPES)
    enabled = models.BooleanField(default=True)
    repo_id = models.CharField(max_length=255, null=True, blank=True)
    auth_required = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Repository'
        verbose_name_plural = 'Repositories'

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('repo_detail', [self.id])

    def show(self):
        """ Show info about this repo, including mirrors
        """
        text = '{0!s} : {1!s}\n'.format(self.id, self.name)
        text += 'security: {0!s}    arch: {1!s}\n'.format(self.security, self.arch)
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
                mirror.file_checksum = None
                mirror.save()

        if not self.auth_required:
            if self.repotype == Repository.DEB:
                refresh_deb_repo(self)
            elif self.repotype == Repository.RPM:
                refresh_rpm_repo(self)
            else:
                text = 'Error: unknown repo type for repo {0!s}: {1!s}'.format(self.id, self.repotype)
                error_message.send(sender=None, text=text)
        else:
            text = 'Repo requires certificate authentication, not updating'
            warning_message.send(sender=None, text=text)

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

    repo = models.ForeignKey(Repository)
    url = models.CharField(max_length=255, unique=True)
    last_access_ok = models.BooleanField(default=False)
    file_checksum = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    packages = models.ManyToManyField(Package,
                                      blank=True,
                                      through='MirrorPackage')
    mirrorlist = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    refresh = models.BooleanField(default=True)
    fail_count = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Mirror'
        verbose_name_plural = 'Mirrors'

    def __unicode__(self):
        return self.url

    @models.permalink
    def get_absolute_url(self):
        return ('mirror_detail', [self.id])

    def show(self):
        """ Show info about this mirror
        """

        text = ' {0!s} : {1!s}\n'.format(self.id, self.url)
        text += ' last updated: {0!s}    checksum: {1!s}\n'.format(self.timestamp,
                                                         self.file_checksum)

        info_message.send(sender=None, text=text)

    def fail(self):
        """ Records that the mirror has failed
            Disables refresh on a mirror if it fails more than 28 times
        """

        text = 'No usable mirror found at {0!s}'.format(self.url)
        error_message.send(sender=None, text=text)
        self.fail_count = self.fail_count + 1
        if self.fail_count > 28:
            self.refresh = False
            text = 'Mirror has failed more than 28 times, disabling refresh'
            error_message.send(sender=None, text=text)

    def update_packages(self, packages):
        """ Update the packages associated with a mirror
        """

        update_mirror_packages(self, packages)


class MirrorPackage(models.Model):
    mirror = models.ForeignKey(Mirror)
    package = models.ForeignKey(Package)
    enabled = models.BooleanField(default=True)
