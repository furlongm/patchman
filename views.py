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

@login_required
def dashboard(request):

    try:
        site = Site.objects.get_current()
    except Site.DoesNotExist:
        site = {'name':'', 'domainname':''}

    stale_hosts = Host.objects.filter(lastreport__lt = (datetime.now() + timedelta(-14)))
    
    norepos = Q(repos__isnull = True) & Q(os__osgroup__repos__isnull = True)
    norepo_hosts = Host.objects.filter(norepos)
    norepo_osgroups = OSGroup.objects.filter(repos__isnull = True)
    
    lonely_oses = OS.objects.filter(osgroup__isnull = True)
    
    secupdates = Q(updates__security = True) & Q(updates__isnull = False)
    updates =  Q(updates__security = False) & Q(updates__isnull = False)
    secupdate_hosts = Host.objects.filter(secupdates).values('hostname').annotate(Count('hostname'))
    update_hosts = Host.objects.filter(updates).values('hostname').annotate(Count('hostname'))

    return render_to_response('dashboard/index.html',
        {'lonely_oses': lonely_oses, 'norepo_hosts': norepo_hosts,
        'stale_hosts': stale_hosts, 'site' : site, 
        'secupdate_hosts' : secupdate_hosts, 'update_hosts' : update_hosts,
        'norepo_osgroups' : norepo_osgroups},
        context_instance=RequestContext(request))

