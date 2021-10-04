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

from django.contrib import admin
from packages.models import Package, PackageName, \
    PackageUpdate, Erratum, ErratumReference


class ErratumAdmin(admin.ModelAdmin):
    readonly_fields = ('packages',)


admin.site.register(Package)
admin.site.register(PackageName)
admin.site.register(PackageUpdate)
admin.site.register(Erratum, ErratumAdmin)
admin.site.register(ErratumReference)
