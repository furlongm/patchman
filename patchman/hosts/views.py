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

from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.contrib import messages
from tagging.models import Tag, TaggedItem

from patchman.util.filterspecs import Filter, FilterBar
from patchman.hosts.models import Host, HostRepo
from patchman.domains.models import Domain
from patchman.arch.models import MachineArchitecture
from patchman.operatingsystems.models import OS, OSGroup
from patchman.reports.models import Report
from patchman.hosts.forms import EditHostForm


@login_required
def host_list(request):

    hosts = Host.objects.select_related()

    if 'domain' in request.GET:
        hosts = hosts.filter(domain=int(request.GET['domain']))

    if 'package_id' in request.GET:
        hosts = hosts.filter(packages=int(request.GET['package_id']))

    if 'package' in request.GET:
        hosts = hosts.filter(packages__name__name=request.GET['package'])

    if 'repo' in request.GET:
        hosts = hosts.filter(repos=int(request.GET['repo']))

    if 'arch' in request.GET:
        hosts = hosts.filter(arch=int(request.GET['arch']))

    if 'os' in request.GET:
        hosts = hosts.filter(os=int(request.GET['os']))

    if 'osgroup' in request.GET:
        hosts = hosts.filter(os__osgroup=int(request.GET['osgroup']))

    if 'tag' in request.GET:
        hosts = TaggedItem.objects.get_by_model(hosts, request.GET['tag'])

    if 'reboot_required' in request.GET:
        reboot_required = request.GET['reboot_required'] == 'True'
        hosts = hosts.filter(reboot_required=reboot_required)

    if 'search' in request.GET:
        terms = request.GET['search'].lower()
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
    filter_list.append(Filter(request, 'arch',
                              MachineArchitecture.objects.all()))
    filter_list.append(Filter(request, 'reboot_required',
                              {False: 'No', True: 'Yes'}))
    filter_bar = FilterBar(request, filter_list)

    return render(request,
                  'hosts/host_list.html',
                  {'page': page,
                   'filter_bar': filter_bar,
                   'terms': terms}, )


@login_required
def host_detail(request, hostname):

    host = get_object_or_404(Host, hostname=hostname)

    reports = Report.objects.filter(host=hostname).order_by('-created')[:3]

    hostrepos = HostRepo.objects.filter(host=host)

    return render(request,
                  'hosts/host_detail.html',
                  {'host': host,
                   'reports': reports,
                   'hostrepos': hostrepos}, )


@login_required
def host_edit(request, hostname):

    host = get_object_or_404(Host, hostname=hostname)

    reports = Report.objects.filter(host=hostname).order_by('-created')[:3]

    if request.method == 'POST':
        edit_form = EditHostForm(request.POST, instance=host)
        if edit_form.is_valid():
            host = edit_form.save()
            host.save()
            messages.info(request, 'Saved changes to Host %s' % host)
            return HttpResponseRedirect(host.get_absolute_url())
        else:
            host = get_object_or_404(Host, hostname=hostname)
    else:
        edit_form = EditHostForm(instance=host)

    return render(request,
                  'hosts/host_edit.html',
                  {'host': host,
                   'reports': reports,
                   'edit_form': edit_form}, )


@login_required
def host_delete(request, hostname):

    host = get_object_or_404(Host, hostname=hostname)

    if request.method == 'POST':
        if 'delete' in request.POST:
            host.delete()
            messages.info(request, 'Host %s has been deleted' % hostname)
            return HttpResponseRedirect(reverse('host_list'))
        elif 'cancel' in request.POST:
            return HttpResponseRedirect(reverse('host_detail',
                                                args=[hostname]))

    reports = Report.objects.filter(host=hostname).order_by('-created')[:3]

    return render(request,
                  'hosts/host_delete.html',
                  {'host': host,
                   'reports': reports}, )
