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

from datetime import datetime, timedelta

from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site
from django.db.models import F

from hosts.models import Host
from operatingsystems.models import OS, OSGroup
from repos.models import Repository, Mirror
from packages.models import Package
from reports.models import Report


@login_required
def dashboard(request):

    try:
        site = Site.objects.get_current()
    except Site.DoesNotExist:
        site = {'name': '', 'domainname': ''}

    hosts = Host.objects.all()
    oses = OS.objects.all()
    osgroups = OSGroup.objects.all()
    repos = Repository.objects.all()
    packages = Package.objects.all()

    # host issues
    if hasattr(settings, 'DAYS_WITHOUT_REPORT') and \
            isinstance(settings.DAYS_WITHOUT_REPORT, int):
        days = settings.DAYS_WITHOUT_REPORT
    else:
        days = 14
    last_report_delta = datetime.now() - timedelta(days=days)
    stale_hosts = hosts.filter(lastreport__lt=last_report_delta)
    norepo_hosts = hosts.filter(repos__isnull=True, os__osgroup__repos__isnull=True)  # noqa
    reboot_hosts = hosts.filter(reboot_required=True)
    secupdate_hosts = hosts.filter(updates__security=True, updates__isnull=False).distinct()  # noqa
    bugupdate_hosts = hosts.exclude(updates__security=True, updates__isnull=False).distinct().filter(updates__security=False, updates__isnull=False).distinct()  # noqa
    diff_rdns_hosts = hosts.exclude(reversedns=F('hostname')).filter(check_dns=True)  # noqa

    # os issues
    lonely_oses = oses.filter(osgroup__isnull=True)
    nohost_oses = oses.filter(host__isnull=True)

    # osgroup issues
    norepo_osgroups = None
    if hosts.filter(host_repos_only=False):
        norepo_osgroups = osgroups.filter(repos__isnull=True)

    # mirror issues
    failed_mirrors = repos.filter(auth_required=False).filter(mirror__last_access_ok=False).filter(mirror__last_access_ok=True).distinct()  # noqa
    disabled_mirrors = repos.filter(auth_required=False).filter(mirror__enabled=False).filter(mirror__mirrorlist=False).distinct()  # noqa
    norefresh_mirrors = repos.filter(auth_required=False).filter(mirror__refresh=False).distinct()  # noqa

    # repo issues
    failed_repos = repos.filter(auth_required=False).filter(mirror__last_access_ok=False).exclude(id__in=[x.id for x in failed_mirrors]).distinct()  # noqa
    unused_repos = repos.filter(host__isnull=True, osgroup__isnull=True)
    nomirror_repos = repos.filter(mirror__isnull=True)
    nohost_repos = repos.filter(host__isnull=True)

    # package issues
    norepo_packages = packages.filter(mirror__isnull=True, oldpackage__isnull=True, host__isnull=False).distinct()  # noqa
    orphaned_packages = packages.filter(mirror__isnull=True, host__isnull=True).distinct()  # noqa

    # report issues
    unprocessed_reports = Report.objects.filter(processed=False)

    checksums = dict()
    possible_mirrors = dict()

    for csvalue in Mirror.objects.all().values('file_checksum').distinct():
        checksum = csvalue['file_checksum']
        if checksum is not None and checksum != 'yast':
            for mirror in Mirror.objects.filter(file_checksum=checksum):
                if mirror.packages.count() > 0:
                    if checksum not in checksums:
                        checksums[checksum] = []
                    checksums[checksum].append(mirror)

    for checksum in checksums:
        first_mirror = checksums[checksum][0]
        for mirror in checksums[checksum]:
            if mirror.repo != first_mirror.repo and \
                    mirror.repo.arch == first_mirror.repo.arch and \
                    mirror.repo.repotype == first_mirror.repo.repotype:
                possible_mirrors[checksum] = checksums[checksum]
                continue

    return render(
        request,
        'dashboard.html',
        {'site': site,
         'lonely_oses': lonely_oses, 'norepo_hosts': norepo_hosts,
         'nohost_oses': nohost_oses, 'diff_rdns_hosts': diff_rdns_hosts,
         'stale_hosts': stale_hosts, 'possible_mirrors': possible_mirrors,
         'norepo_packages': norepo_packages,
         'nohost_repos': nohost_repos,
         'secupdate_hosts': secupdate_hosts,
         'bugupdate_hosts': bugupdate_hosts,
         'norepo_osgroups': norepo_osgroups, 'unused_repos': unused_repos,
         'disabled_mirrors': disabled_mirrors,
         'norefresh_mirrors': norefresh_mirrors,
         'failed_mirrors': failed_mirrors,
         'orphaned_packages': orphaned_packages,
         'failed_repos': failed_repos, 'nomirror_repos': nomirror_repos,
         'reboot_hosts': reboot_hosts,
         'unprocessed_reports': unprocessed_reports}, )
