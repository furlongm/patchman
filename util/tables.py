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

import django_tables2 as tables


class BaseTable(tables.Table):
    """Base table class with common settings for all patchman tables."""

    class Meta:
        abstract = True
        template_name = 'table.html'
        attrs = {
            "class": "table table-striped table-bordered table-hover table-condensed table-responsive",
        }
