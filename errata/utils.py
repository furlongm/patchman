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

from util import tz_aware_datetime
from errata.models import Erratum
from patchman.signals import pbar_start, pbar_update, warning_message


def get_or_create_erratum(name, e_type, issue_date, synopsis):
    """ Get or create an Erratum object. Returns the object and created
    """
    try:
        e = Erratum.objects.get(name=name)
        issue_date_tz = tz_aware_datetime(issue_date)
        # if it's +/- 1 day we don't update it, just use whichever was the first one
        # different sources are generated at different times
        # e.g. yum updateinfo vs website errata info
        days_delta = abs(e.issue_date.date() - issue_date_tz.date()).days
        updated = False
        if e.e_type != e_type:
            warning_message.send(sender=None, text=f'Updating {name} type `{e.e_type}` -> `{e_type}`')
            e.e_type = e_type
            updated = True
        if days_delta > 1:
            text = f'Updating {name} issue date `{e.issue_date.date()}` -> `{issue_date_tz.date()}`'
            warning_message.send(sender=None, text=text)
            e.issue_date = issue_date_tz
            updated = True
        if e.synopsis != synopsis:
            warning_message.send(sender=None, text=f'Updating {name} synopsis `{e.synopsis}` -> `{synopsis}`')
            e.synopsis = synopsis
            updated = True
        if updated:
            e.save()
        created = False
    except Erratum.DoesNotExist:
        e, created = Erratum.objects.get_or_create(
            name=name,
            e_type=e_type,
            issue_date=tz_aware_datetime(issue_date),
            synopsis=synopsis,
        )
    return e, created


def mark_errata_security_updates():
    """ For each set of erratum packages, modify any PackageUpdate that
        should be marked as a security update.
    """
    elen = Erratum.objects.count()
    pbar_start.send(sender=None, ptext=f'Scanning {elen} Errata', plen=elen)
    for i, e in enumerate(Erratum.objects.all()):
        pbar_update.send(sender=None, index=i + 1)
        e.scan_for_security_updates()
