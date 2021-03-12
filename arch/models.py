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


class Architecture(models.Model):

    name = models.CharField(unique=True, max_length=255)

    class Meta(object):
        abstract = True

    def __str__(self):
        return self.name


class MachineArchitecture(Architecture):

    class Meta(Architecture.Meta):
        verbose_name = 'Machine Architecture'


class PackageArchitecture(Architecture):

    class Meta(Architecture.Meta):
        verbose_name = 'Package Architecture'
