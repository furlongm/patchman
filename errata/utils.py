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

import concurrent.futures

import requests
from requests.adapters import HTTPAdapter

from errata.models import Erratum
from packages.models import PackageUpdate
from patchman.signals import pbar_start, pbar_update
from util import run_concurrently, tz_aware_datetime
from util.logging import error_message, warning_message


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
            warning_message(text=f'Updating {name} type `{e.e_type}` -> `{e_type}`')
            e.e_type = e_type
            updated = True
        if days_delta > 1:
            text = f'Updating {name} issue date `{e.issue_date.date()}` -> `{issue_date_tz.date()}`'
            warning_message(text=text)
            e.issue_date = issue_date_tz
            updated = True
        if e.synopsis != synopsis:
            warning_message(text=f'Updating {name} synopsis `{e.synopsis}` -> `{synopsis}`')
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


def mark_errata_security_updates(concurrent_processing=True, max_workers=25):
    """ For each set of erratum packages, modify any PackageUpdate that
        should be marked as a security update.
    """
    elen = Erratum.objects.count()
    pbar_start.send(sender=None, ptext=f'Scanning {elen} Errata for security updates', plen=elen)
    if concurrent_processing:
        pks = list(Erratum.objects.values_list('pk', flat=True))
        for i, _ in enumerate(run_concurrently(_scan_security_worker, pks, max_workers)):
            pbar_update.send(sender=None, index=i + 1)
    else:
        for i, e in enumerate(Erratum.objects.all()):
            e.scan_for_security_updates()
            pbar_update.send(sender=None, index=i + 1)


def _scan_security_worker(pk):
    e = Erratum.objects.get(pk=pk)
    return e.scan_for_security_updates()


def scan_package_updates_for_affected_packages():
    """ Scan PackageUpdates for packages affected by errata
    """
    plen = PackageUpdate.objects.count()
    pbar_start.send(sender=None, ptext=f'Scanning {plen} Updates for affected packages', plen=plen)
    for i, pu in enumerate(PackageUpdate.objects.all()):
        pbar_update.send(sender=None, index=i + 1)
        for e in pu.newpackage.provides_fix_in_erratum.all():
            e.affected_packages.add(pu.oldpackage)


def enrich_errata(concurrent_processing=True, max_workers=25):
    """ Enrich Errata with data from osv.dev
    """
    errata = list(Erratum.objects.all())
    elen = len(errata)

    # phase 1: fetch osv.dev data
    pbar_start.send(sender=None, ptext=f'Fetching osv.dev data for {elen} Errata', plen=elen)
    results = []
    if concurrent_processing:
        session = requests.Session()
        adapter = HTTPAdapter(pool_connections=max_workers, pool_maxsize=max_workers)
        session.mount('https://', adapter)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(e.fetch_osv_dev_data, session): e for e in errata}
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                erratum = futures[future]
                try:
                    osv_data = future.result()
                except Exception as e:
                    error_message(text=f'Error fetching osv.dev data for {erratum}: {e}')
                    pbar_update.send(sender=None, index=i + 1)
                    continue
                if osv_data is not None:
                    results.append((erratum, osv_data))
                pbar_update.send(sender=None, index=i + 1)
    else:
        for i, e in enumerate(errata):
            osv_data = e.fetch_osv_dev_data()
            if osv_data is not None:
                results.append((e, osv_data))
            pbar_update.send(sender=None, index=i + 1)

    # phase 2: parse and write to db (serial, no lock contention)
    rlen = len(results)
    if rlen > 0:
        pbar_start.send(sender=None, ptext=f'Parsing osv.dev data for {rlen} Errata', plen=rlen)
        for i, (erratum, osv_data) in enumerate(results):
            erratum.parse_osv_dev_data(osv_data)
            pbar_update.send(sender=None, index=i + 1)
