# Copyright 2023 Marcus Furlong <furlongm@gmail.com>
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

from arch.models import PackageArchitecture
from packages.models import Package
from repos.models import Repository


class Module(models.Model):

    name = models.CharField(unique=True, max_length=255)
    stream = models.CharField(unique=True, max_length=255)
    version = models.CharField(max_length=255)
    context = models.CharField(unique=True, max_length=255)
    arch = models.ForeignKey(PackageArchitecture, on_delete=models.CASCADE)
    repo = models.ForeignKey(Repository, on_delete=models.CASCADE)
    packages = models.ManyToManyField(Package, blank=True)

    class Meta:
        verbose_name = 'Module'
        verbose_name_plural = 'Modules'
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('modules:module_detail', args=[str(self.id)])
