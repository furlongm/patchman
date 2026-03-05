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

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site
from django.db.models import F
from django.shortcuts import render
from django.utils import timezone

from hosts.models import Host
from operatingsystems.models import OSRelease, OSVariant
from packages.models import Package
from reports.models import Report
from repos.models import Mirror, Repository
from util import get_setting_of_type


@login_required
def dashboard(request):

    try:
        site = Site.objects.get_current()
    except Site.DoesNotExist:
        site = {'name': '', 'domainname': ''}

    return render(request, 'dashboard.html', {'site': site})


@login_required
def issues(request):

    try:
        site = Site.objects.get_current()
    except Site.DoesNotExist:
        site = {'name': '', 'domainname': ''}

    hosts = Host.objects.all()
    repos = Repository.objects.all()

    # host issues
    days = get_setting_of_type(
        setting_name='DAYS_WITHOUT_REPORT',
        setting_type=int,
        default=14,
    )
    last_report_delta = timezone.now() - timedelta(days=days)
    counts = {
        'stale_hosts': hosts.filter(lastreport__lt=last_report_delta).count(),
        'norepo_hosts': hosts.filter(repos__isnull=True, osvariant__osrelease__repos__isnull=True).count(),
        'reboot_hosts': hosts.filter(reboot_required=True).count(),
        'secupdate_hosts': hosts.filter(sec_updates_count__gt=0).count(),
        'bugupdate_hosts': hosts.filter(bug_updates_count__gt=0, sec_updates_count=0).count(),
        'diff_rdns_hosts': hosts.exclude(reversedns=F('hostname')).filter(check_dns=True).count(),
        'noosrelease_osvariants': OSVariant.objects.filter(osrelease__isnull=True).count(),
        'nohost_osvariants': OSVariant.objects.filter(host__isnull=True).count(),
        'norepo_osreleases': 0,
    }

    if hosts.filter(host_repos_only=False).exists():
        counts['norepo_osreleases'] = OSRelease.objects.filter(repos__isnull=True).count()

    # mirror issues — chained .filter() on M2M creates separate JOINs,
    # so this finds repos with BOTH a failing AND a succeeding mirror
    failed_mirrors_qs = repos.filter(auth_required=False).filter(mirror__last_access_ok=False).filter(mirror__last_access_ok=True).distinct()  # noqa
    failed_mirror_ids = list(failed_mirrors_qs.values_list('id', flat=True))
    counts['failed_mirrors'] = len(failed_mirror_ids)
    counts['disabled_mirrors'] = repos.filter(auth_required=False, mirror__enabled=False, mirror__mirrorlist=False).distinct().count()  # noqa
    counts['norefresh_mirrors'] = repos.filter(auth_required=False, mirror__refresh=False).distinct().count()

    # repo issues — all mirrors failing = has failing mirrors but not in partial-failure set
    counts['failed_repos'] = repos.filter(auth_required=False, mirror__last_access_ok=False).exclude(id__in=failed_mirror_ids).distinct().count()  # noqa
    counts['unused_repos'] = repos.filter(host__isnull=True, osrelease__isnull=True).count()
    counts['nomirror_repos'] = repos.filter(mirror__isnull=True).count()
    counts['nohost_repos'] = repos.filter(host__isnull=True).count()

    # package issues
    counts['norepo_packages'] = Package.objects.filter(mirror__isnull=True, oldpackage__isnull=True, host__isnull=False).distinct().count()  # noqa
    counts['orphaned_packages'] = Package.objects.filter(mirror__isnull=True, host__isnull=True).count()

    # report issues
    counts['unprocessed_reports'] = Report.objects.filter(processed=False).count()

    # possible mirrors (checksum duplicates across repos)
    checksums = {}
    possible_mirrors = {}
    for csvalue in Mirror.objects.filter(packages_count__gt=0).values('packages_checksum').distinct():
        checksum = csvalue['packages_checksum']
        if checksum is not None and checksum != 'yast':
            mirrors = list(Mirror.objects.filter(
                packages_checksum=checksum,
                packages_count__gt=0
            ).select_related('repo'))
            if mirrors:
                checksums[checksum] = mirrors

    for checksum in checksums:
        first_mirror = checksums[checksum][0]
        for mirror in checksums[checksum]:
            if mirror.repo != first_mirror.repo and \
                    mirror.repo.arch == first_mirror.repo.arch and \
                    mirror.repo.repotype == first_mirror.repo.repotype:
                possible_mirrors[checksum] = checksums[checksum]
                continue

    has_issues = any(counts.values()) or bool(possible_mirrors)

    return render(
        request,
        'issues.html',
        {'site': site,
         'has_issues': has_issues,
         'possible_mirrors': possible_mirrors,
         **counts})
