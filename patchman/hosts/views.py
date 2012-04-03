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

from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.contrib import messages
from tagging.models import Tag

from andsome.util.filterspecs import Filter, FilterBar
import socket

from patchman.hosts.models import Host, HostRepo
from patchman.domains.models import Domain
from patchman.arch.models import MachineArchitecture
from patchman.operatingsystems.models import OS, OSGroup
from patchman.reports.models import Report
from patchman.hosts.forms import HostForm


@login_required
def host_list(request):

    hosts = Host.objects.select_related()

    if 'domain' in request.REQUEST:
        hosts = hosts.filter(domain=int(request.REQUEST['domain']))

    if 'package_id' in request.REQUEST:
        hosts = hosts.filter(packages=int(request.REQUEST['package_id']))

    if 'package' in request.REQUEST:
        hosts = hosts.filter(packages__name__name=request.REQUEST['package'])

    if 'repo' in request.REQUEST:
        hosts = hosts.filter(repos=int(request.REQUEST['repo']))

    if 'arch' in request.REQUEST:
        hosts = hosts.filter(arch=int(request.REQUEST['arch']))

    if 'os' in request.REQUEST:
        hosts = hosts.filter(os=int(request.REQUEST['os']))

    if 'osgroup' in request.REQUEST:
        hosts = hosts.filter(os__osgroup=int(request.REQUEST['osgroup']))

    if 'tag' in request.REQUEST:
        hosts = hosts.filter(tags=request.REQUEST['tag'])

    if 'reboot_required' in request.REQUEST:
        reboot_required = request.REQUEST['reboot_required'] == 'True'
        hosts = hosts.filter(reboot_required=reboot_required)

    if 'search' in request.REQUEST:
        terms = request.REQUEST['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(hostname__icontains=term)
            query = query & q
        hosts = hosts.filter(query)
    else:
        terms = ''

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
        mytags[tag.name] = tag.name
    filter_list.append(Filter(request, 'tag', mytags))
    filter_list.append(Filter(request, 'domain', Domain.objects.all()))
    filter_list.append(Filter(request, 'os', OS.objects.all()))
    filter_list.append(Filter(request, 'osgroup', OSGroup.objects.all()))
    filter_list.append(Filter(request, 'arch', MachineArchitecture.objects.all()))
    filter_list.append(Filter(request, 'reboot_required', {False: 'No', True: 'Yes'}))
    filter_bar = FilterBar(request, filter_list)

    return render_to_response('hosts/host_list.html', {'page': page, 'filter_bar': filter_bar, 'terms': terms}, context_instance=RequestContext(request))


@login_required
def host_detail(request, hostname):

    host = get_object_or_404(Host, hostname=hostname)

    try:
        reversedns = str(socket.gethostbyaddr(host.ipaddress)[0])
    except socket.gaierror:
        reversedns = 'None'

    reports = Report.objects.all().filter(host=hostname).order_by('-time')[:3]

    hostrepos = HostRepo.objects.filter(host=host)

    return render_to_response('hosts/host_detail.html', {'host': host, 'reversedns': reversedns, 'reports': reports, 'hostrepos': hostrepos}, context_instance=RequestContext(request))


@login_required
def host_edit(request, hostname):

    host = get_object_or_404(Host, hostname=hostname)

    try:
        reversedns = str(socket.gethostbyaddr(host.ipaddress)[0])
    except socket.gaierror:
        reversedns = 'None'

    reports = Report.objects.all().filter(host=hostname).order_by('-time')[:3]

    if request.method == 'POST':
        edit_form = HostForm(request.POST, instance=host)
        if edit_form.is_valid():
            host = edit_form.save()
            host.save()
            messages.info(request, 'Saved changes to Host %s' % host)
            return HttpResponseRedirect(host.get_absolute_url())
        else:
            host = get_object_or_404(Host, hostname=hostname)
    else:
        edit_form = HostForm(instance=host)

    return render_to_response('hosts/host_edit.html', {'host': host, 'reversedns': reversedns, 'reports': reports, 'edit_form': edit_form}, context_instance=RequestContext(request))


@login_required
def host_delete(request, hostname):

    host = get_object_or_404(Host, hostname=hostname)

    if request.method == 'POST':
        if 'delete' in request.REQUEST:
            host.delete()
            messages.info(request, 'Host %s has been deleted' % hostname)
            return HttpResponseRedirect(reverse('host_list'))
        elif 'cancel' in request.REQUEST:
            return HttpResponseRedirect(reverse('host_detail', args=[hostname]))

    try:
        reversedns = str(socket.gethostbyaddr(host.ipaddress)[0])
    except socket.gaierror:
        reversedns = 'None'

    reports = Report.objects.all().filter(host=hostname).order_by('-time')[:3]

    return render_to_response('hosts/host_delete.html', {'host': host, 'reversedns': reversedns, 'reports': reports}, context_instance=RequestContext(request))
