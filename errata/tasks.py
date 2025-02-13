# Copyright 2025 Marcus Furlong <furlongm@gmail.com>
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

from celery import shared_task

from errata.models import Erratum
from security.tasks import update_cves, update_cwes


@shared_task
def update_erratum(erratum):
    """ Task to update an erratum
    """
    erratum.update()


@shared_task
def update_errata():
    """ Task to update all errata
    """
    for e in Erratum.objects.all():
        update_erratum.delay(e)
    update_cves.delay()
    update_cwes.delay()
