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

from repos.models import Repository


class OSGroup(models.Model):

    name = models.CharField(max_length=255, unique=True)
    repos = models.ManyToManyField(Repository, blank=True)

    class Meta(object):
        verbose_name = 'Operating System Group'
        verbose_name_plural = 'Operating System Groups'
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('operatingsystems:osgroup_detail', args=[str(self.id)])


class OS(models.Model):

    name = models.CharField(max_length=255, unique=True)
    osgroup = models.ForeignKey(OSGroup, blank=True, null=True,
                                on_delete=models.SET_NULL)

    class Meta(object):
        verbose_name = 'Operating System'
        verbose_name_plural = 'Operating Systems'
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('operatingsystems:os_detail', args=[str(self.id)])
