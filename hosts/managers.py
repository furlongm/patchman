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
from django.db.models import Count, Q
from django.db.models.functions import Coalesce


class HostManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related()

    def with_counts(self, *properties):
        """
        Overwrite count methods with annotated values. Used for
        template rendering which detects if something is a
        callable automatically.
        """
        available_properties = {
            'get_num_security_updates': Coalesce(
                Count(
                    'updates',
                    filter=Q(updates__security=True),
                    distinct=True,
                ),
                0,
            ),
            'get_num_bugfix_updates': Coalesce(
                Count(
                    'updates',
                    filter=Q(updates__security=False),
                    distinct=True,
                ),
                0,
            ),
        }

        return self.get_queryset() \
            .annotate(**{prop: available_properties[prop] for prop in properties}) \
            .order_by(*self.model._meta.ordering)  # not sure why, but it's not applied
