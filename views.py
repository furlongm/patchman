# Copyright 2011 VPAC <furlongm@vpac.org>
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

from django.utils.datastructures import MultiValueDictKeyError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import permission_required, login_required
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.db.models import Q, Count

from datetime import datetime, date, time, timedelta

from patchman.hosts.models import Host
from patchman.operatingsystems.models import OS, OSGroup
from patchman.repos.models import Repository
from patchman.packages.models import Package, PackageName

@login_required
def dashboard(request):

    try:
        site = Site.objects.get_current()
    except Site.DoesNotExist:
        site = {'name':'', 'domainname':''}

    stale_hosts = Host.objects.filter(lastreport__lt = (datetime.now() + timedelta(-14)))
    stale_repos = Repository.objects.filter(timestamp__lt = (datetime.now() + timedelta(-14)))
    norepo_hosts = Host.objects.filter(repos__isnull = True, os__osgroup__repos__isnull = True)
    norepo_osgroups = OSGroup.objects.filter(repos__isnull = True)
    norepo_packages = Package.objects.filter(repository__isnull = True)
    lonely_oses = OS.objects.filter(osgroup__isnull = True)
    failed_repos = Repository.objects.filter(last_access_ok = False)
    secupdate_hosts = Host.objects.filter(updates__security = True, updates__isnull = False).values('hostname').annotate(Count('hostname'))
    update_hosts = Host.objects.filter(updates__security = False, updates__isnull = False).values('hostname').annotate(Count('hostname'))
    unused_repos = Repository.objects.filter(host__isnull = True, osgroup__isnull = True)

    return render_to_response('dashboard/index.html',
        {'lonely_oses': lonely_oses, 'norepo_hosts': norepo_hosts,
        'stale_hosts': stale_hosts, 'stale_repos': stale_repos,
        'site' : site, 'norepo_packages' : norepo_packages, 
        'secupdate_hosts' : secupdate_hosts, 'update_hosts' : update_hosts,
        'norepo_osgroups' : norepo_osgroups, 'unused_repos': unused_repos,
        'failed_repos' : failed_repos},
        context_instance=RequestContext(request))

