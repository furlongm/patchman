# Copyright 2012 VPAC, http://www.vpac.org
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

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site
from django.db.models import Count

from datetime import datetime, timedelta

from patchman.hosts.models import Host
from patchman.operatingsystems.models import OS, OSGroup
from patchman.repos.models import Repository, Mirror
from patchman.packages.models import Package
from patchman.reports.models import Report


@login_required
def dashboard(request):

    try:
        site = Site.objects.get_current()
    except Site.DoesNotExist:
        site = {'name': '', 'domainname': ''}

    stale_hosts = Host.objects.filter(lastreport__lt=(datetime.now() + timedelta(-14)))
    norepo_hosts = Host.objects.filter(repos__isnull=True, os__osgroup__repos__isnull=True)
    norepo_osgroups = OSGroup.objects.filter(repos__isnull=True)
    norepo_packages = Package.objects.filter(mirror__isnull=True, oldpackage__isnull=True)
    orphaned_packages = Package.objects.filter(mirror__isnull=True, host__isnull=True)
    lonely_oses = OS.objects.filter(osgroup__isnull=True)
    failed_mirrors = Repository.objects.filter(mirror__last_access_ok=False).filter(mirror__last_access_ok=True).distinct()
    failed_repos = Repository.objects.filter(mirror__last_access_ok=False).exclude(id__in=[x.id for x in failed_mirrors]).distinct()
    reboot_hosts = Host.objects.filter(reboot_required=True)
    secupdate_hosts = Host.objects.filter(updates__security=True, updates__isnull=False).values('hostname').annotate(Count('hostname'))
    update_hosts = Host.objects.filter(updates__security=False, updates__isnull=False).values('hostname').annotate(Count('hostname'))
    unused_repos = Repository.objects.filter(host__isnull=True, osgroup__isnull=True)
    unprocessed_reports = Report.objects.filter(processed=False)
    nomirror_repos = Repository.objects.filter(mirror__isnull=True)
    nohost_repos = Repository.objects.filter(host__isnull=True)

    checksums = dict()
    possible_mirrors = dict()

    for csvalue in Mirror.objects.all().values('file_checksum').distinct():
        checksum = csvalue['file_checksum']
        if checksum != None:
            for mirror in Mirror.objects.filter(file_checksum=checksum):
                if mirror.packages.count() > 0:
                    if not checksum in checksums:
                        checksums[checksum] = []
                    checksums[checksum].append(mirror)
    
    for checksum in checksums:
        first_mirror = checksums[checksum][0]
        for mirror in checksums[checksum]:
            if mirror.repo != first_mirror.repo:
                possible_mirrors[checksum] = checksums[checksum]
                continue

    return render_to_response('dashboard/index.html',
        {'lonely_oses': lonely_oses, 'norepo_hosts': norepo_hosts,
        'stale_hosts': stale_hosts, 'possible_mirrors': possible_mirrors,
        'site': site, 'norepo_packages': norepo_packages, 'nohost_repos': nohost_repos,
        'secupdate_hosts': secupdate_hosts, 'update_hosts': update_hosts,
        'norepo_osgroups': norepo_osgroups, 'unused_repos': unused_repos,
        'failed_mirrors': failed_mirrors, 'orphaned_packages': orphaned_packages,
        'failed_repos': failed_repos, 'nomirror_repos': nomirror_repos,
        'reboot_hosts': reboot_hosts, 'unprocessed_reports': unprocessed_reports},
        context_instance=RequestContext(request))
