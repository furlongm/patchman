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

from patchman.repos.utils import update_deb_repo, update_rpm_repo, update_mirror_packages
from patchman.signals import error_message, info_message


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
        verbose_name_plural = 'Repositories'

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('repo_detail', [self.id])

    def update(self, force=False):
        """ Update all of a repos mirror metadata,
            force can be set to force a reset of all the mirrors metadata
        """

        if force:
            for mirror in self.mirror_set.all():
                mirror.file_checksum = None
                mirror.save()

        if not self.auth_required:
            if self.repotype == Repository.DEB:
                update_deb_repo(self)
            elif self.repotype == Repository.RPM:
                update_rpm_repo(self)
            else:
                error_message.send(sender=None, text='Error: unknown repo type for repo %s: %s\n' % (self.id, self.repotype))
        else:
            info_message.send(sender=None, text='Repo requires certificate authentication, not updating\n')


class Mirror(models.Model):

    repo = models.ForeignKey(Repository)
    url = models.CharField(max_length=255, unique=True)
    last_access_ok = models.BooleanField()
    file_checksum = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    packages = models.ManyToManyField(Package, blank=True, null=True, through='MirrorPackage')
    mirrorlist = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    refresh = models.BooleanField(default=True)
    fail_count = models.IntegerField(default=0)

    def __unicode__(self):
        return self.url

    def fail(self):
        """ Records that the mirror has failed
            Disables refresh on a mirror if it fails more than 28 times
        """

        error_message.send(sender=None, text='No usable mirror found at %s\n' % self.url)
        self.fail_count = self.fail_count + 1
        if self.fail_count > 28:
            self.refresh = False
            error_message.send(sender=None, text='Mirror has failed more than 28 times, disabling refresh\n')

    def update_packages(self, packages):
        """ Update the packages associated with a mirror
        """

        update_mirror_packages(self, packages)

        
class MirrorPackage(models.Model):
    mirror = models.ForeignKey(Mirror)
    package = models.ForeignKey(Package)
    enabled = models.BooleanField(default=True)
