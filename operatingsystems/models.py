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
from repos.models import Repository


class OSRelease(models.Model):

    name = models.CharField(max_length=255, unique=True, blank=False, null=False)
    repos = models.ManyToManyField(Repository, blank=True)
    codename = models.CharField(max_length=255, blank=True)
    cpe_name = models.CharField(max_length=255, null=True, blank=True, unique=True)

    from operatingsystems.managers import OSReleaseManager
    objects = OSReleaseManager()

    class Meta:
        verbose_name = 'Operating System Release'
        verbose_name_plural = 'Operating System Releases'
        unique_together = ['name', 'codename', 'cpe_name']
        ordering = ['name']

    def __str__(self):
        if self.codename:
            return f'{self.name} ({self.codename})'
        else:
            return self.name

    def get_absolute_url(self):
        return reverse('operatingsystems:osrelease_detail', args=[str(self.id)])

    def natural_key(self):
        return (self.name, self.codename, self.cpe_name)


class OSVariant(models.Model):

    name = models.CharField(max_length=255, unique=True)
    arch = models.ForeignKey(MachineArchitecture, blank=True, null=True, on_delete=models.CASCADE)
    osrelease = models.ForeignKey(OSRelease, blank=True, null=True, on_delete=models.SET_NULL)
    codename = models.CharField(max_length=255, blank=True)
    # Cached count field for query optimization
    hosts_count = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        verbose_name = 'Operating System Variant'
        verbose_name_plural = 'Operating System Variants'
        ordering = ['name']

    def __str__(self):
        osvariant_name = f'{self.name} {self.arch}'
        return osvariant_name

    def get_absolute_url(self):
        return reverse('operatingsystems:osvariant_detail', args=[str(self.id)])
