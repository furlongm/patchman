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
from patchman.repos.models import Repository


class OSGroup(models.Model):

    name = models.CharField(max_length=255, unique=True)
    repos = models.ManyToManyField(Repository, blank=True, null=True)

    class Meta:
        verbose_name = 'Operating System Group'

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('osgroup_detail', [self.id])


class OS(models.Model):

    name = models.CharField(max_length=255, unique=True)
# Django 1.3+
#    osgroup = models.ForeignKey(OSGroup, blank=True, null=True, on_delete=models.SET_NULL)
    osgroup = models.ForeignKey(OSGroup, blank=True, null=True)

    class Meta:
        verbose_name = 'Operating System'

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('os_detail', [self.id])
