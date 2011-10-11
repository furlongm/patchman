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
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count
from django.contrib import messages
from tagging.models import Tag, TaggedItem

from andsome.util.filterspecs import Filter, FilterBar
from datetime import datetime, date, time
import socket

from patchman.hosts.models import Host
from patchman.domains.models import Domain
from patchman.packages.models import Package, PackageName
from patchman.arch.models import MachineArchitecture
from patchman.repos.models import Repository
from patchman.operatingsystems.models import OS, OSGroup
from patchman.reports.models import Report

@login_required
def host_list(request):

    hosts = Host.objects.select_related()
    
    if request.REQUEST.has_key('domain'):
        hosts = hosts.filter(domain=int(request.GET['domain']))

    if request.REQUEST.has_key('package_id'):
        hosts = hosts.filter(packages=int(request.GET['package_id']))

    if request.REQUEST.has_key('package'):
        hosts = hosts.filter(packages__name__name=request.GET['package'])

    if request.REQUEST.has_key('repo'):
        hosts = hosts.filter(repos=int(request.GET['repo']))

    if request.REQUEST.has_key('arch'):
        hosts = hosts.filter(arch=int(request.GET['arch']))

    if request.REQUEST.has_key('os'):
        hosts = hosts.filter(os=int(request.GET['os']))

    if request.REQUEST.has_key('osgroup'):
        hosts = hosts.filter(os__osgroup=int(request.GET['osgroup']))
        
    if request.REQUEST.has_key('tag'):
#        hosts = TaggedItem.objects.get_by_model(Host, request.GET['tag'])
        hosts = hosts.filter(tags=request.GET['tag'])

    if request.REQUEST.has_key('search'):
        new_data = request.POST.copy()
        terms = new_data['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(hostname__icontains = term)
            query = query & q
        hosts = hosts.filter(query)
    else:
        terms = ""

    try:
        page_no = int(request.GET.get('page', 1))
    except ValueError:
        page_no = 1

    p = Paginator(hosts, 50)

    try:
        page = p.page(page_no)
    except (EmptyPage, InvalidPage):
        page = p.page(p.num_pages)

    filter_list = []
    mytags = {}
    for tag in Tag.objects.usage_for_model(Host):
        mytags[tag.name]=tag.name
    filter_list.append(Filter(request, 'tag', mytags))
    filter_list.append(Filter(request, 'domain', Domain.objects.all()))
    filter_list.append(Filter(request, 'os', OS.objects.all()))
    filter_list.append(Filter(request, 'osgroup', OSGroup.objects.all()))
    filter_list.append(Filter(request, 'arch', MachineArchitecture.objects.all()))
    filter_bar = FilterBar(request, filter_list)

    return render_to_response('hosts/host_list.html', {'page': page, 'filter_bar': filter_bar}, context_instance=RequestContext(request))


@login_required
def host_detail(request, hostname):

    host = get_object_or_404(Host, hostname=hostname)

    try:
        reversedns = str(socket.gethostbyaddr(host.ipaddress)[0])
    except socket.gaierror:
        reversedns = 'None'

    reports = Report.objects.all().filter(host=hostname).order_by('-time')[:3]
 
    return render_to_response('hosts/host_detail.html', {'host': host, 'reversedns': reversedns, 'reports': reports }, context_instance=RequestContext(request))

@login_required
def host_delete(request, hostname):

    host = get_object_or_404(Host, hostname=hostname)

    if request.method == 'POST':
        if request.REQUEST.has_key('delete'):
            host.delete()
            messages.info(request, "Host %s has been deleted." % hostname)
            return HttpResponseRedirect(reverse('host_list'))
        elif request.REQUEST.has_key('cancel'):
            return HttpResponseRedirect(reverse('host_detail', args=[hostname]))

    try:
        reversedns = str(socket.gethostbyaddr(host.ipaddress)[0])
    except socket.gaierror:
        reversedns = 'None'

    return render_to_response('hosts/host_delete.html', {'host': host, 'reversedns': reversedns}, context_instance=RequestContext(request))
