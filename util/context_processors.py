# Copyright 2013-2025 Marcus Furlong <furlongm@gmail.com>
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

from datetime import datetime, timedelta

from django.db.models import F

from hosts.models import Host
from operatingsystems.models import OSRelease, OSVariant
from reports.models import Report
from repos.models import Repository
from util import get_setting_of_type


def issues_count(request):
    """Context processor to provide issues count for navbar."""
    if not request.user.is_authenticated:
        return {'issues_count': 0}

    hosts = Host.objects.all()
    osvariants = OSVariant.objects.all()
    osreleases = OSRelease.objects.all()
    repos = Repository.objects.all()

    # host issues
    days = get_setting_of_type(
        setting_name='DAYS_WITHOUT_REPORT',
        setting_type=int,
        default=14,
    )
    last_report_delta = datetime.now() - timedelta(days=days)
    stale_hosts = hosts.filter(lastreport__lt=last_report_delta)
    norepo_hosts = hosts.filter(repos__isnull=True, osvariant__osrelease__repos__isnull=True)
    reboot_hosts = hosts.filter(reboot_required=True)
    secupdate_hosts = hosts.filter(updates__security=True, updates__isnull=False).distinct()
    bugupdate_hosts = hosts.exclude(
        updates__security=True, updates__isnull=False
    ).distinct().filter(
        updates__security=False, updates__isnull=False
    ).distinct()
    diff_rdns_hosts = hosts.exclude(reversedns=F('hostname')).filter(check_dns=True)

    # os variant issues
    noosrelease_osvariants = osvariants.filter(osrelease__isnull=True)
    nohost_osvariants = osvariants.filter(host__isnull=True)

    # os release issues
    norepo_osreleases_count = 0
    if hosts.filter(host_repos_only=False).exists():
        norepo_osreleases_count = osreleases.filter(repos__isnull=True).count()

    # mirror issues
    failed_mirrors = repos.filter(
        auth_required=False, mirror__last_access_ok=False
    ).filter(mirror__last_access_ok=True).distinct()
    disabled_mirrors = repos.filter(
        auth_required=False, mirror__enabled=False, mirror__mirrorlist=False
    ).distinct()
    norefresh_mirrors = repos.filter(auth_required=False, mirror__refresh=False).distinct()

    # repo issues
    failed_repos = repos.filter(
        auth_required=False, mirror__last_access_ok=False
    ).exclude(id__in=[x.id for x in failed_mirrors]).distinct()
    unused_repos = repos.filter(host__isnull=True, osrelease__isnull=True)
    nomirror_repos = repos.filter(mirror__isnull=True)
    nohost_repos = repos.filter(host__isnull=True)

    # report issues
    unprocessed_reports = Report.objects.filter(processed=False)

    count = (
        (1 if stale_hosts.exists() else 0) +
        (1 if norepo_hosts.exists() else 0) +
        (1 if reboot_hosts.exists() else 0) +
        (1 if secupdate_hosts.exists() else 0) +
        (1 if bugupdate_hosts.exists() else 0) +
        (1 if diff_rdns_hosts.exists() else 0) +
        (1 if noosrelease_osvariants.exists() else 0) +
        (1 if nohost_osvariants.exists() else 0) +
        (1 if norepo_osreleases_count > 0 else 0) +
        (1 if failed_mirrors.exists() else 0) +
        (1 if disabled_mirrors.exists() else 0) +
        (1 if norefresh_mirrors.exists() else 0) +
        (1 if failed_repos.exists() else 0) +
        (1 if unused_repos.exists() else 0) +
        (1 if nomirror_repos.exists() else 0) +
        (1 if nohost_repos.exists() else 0) +
        (1 if unprocessed_reports.exists() else 0)
    )

    return {'issues_count': count}
