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

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from rest_framework import viewsets
from taggit.models import Tag

from arch.models import MachineArchitecture
from domains.models import Domain
from hosts.forms import EditHostForm
from hosts.models import Host, HostRepo
from hosts.serializers import HostRepoSerializer, HostSerializer
from operatingsystems.models import OSRelease, OSVariant
from reports.models import Report
from util.filterspecs import Filter, FilterBar


@login_required
def host_list(request):
    hosts = Host.objects.select_related()

    if 'domain_id' in request.GET:
        hosts = hosts.filter(domain=request.GET['domain_id'])

    if 'package_id' in request.GET:
        hosts = hosts.filter(packages=request.GET['package_id'])

    if 'package' in request.GET:
        hosts = hosts.filter(packages__name__name=request.GET['package'])

    if 'repo_id' in request.GET:
        hosts = hosts.filter(repos=request.GET['repo_id'])

    if 'arch_id' in request.GET:
        hosts = hosts.filter(arch=request.GET['arch_id'])

    if 'osvariant_id' in request.GET:
        hosts = hosts.filter(osvariant=request.GET['osvariant_id'])

    if 'osrelease_id' in request.GET:
        hosts = hosts.filter(osvariant__osrelease=request.GET['osrelease_id'])

    if 'tag' in request.GET:
        hosts = hosts.filter(tags__name__in=[request.GET['tag']])

    if 'reboot_required' in request.GET:
        reboot_required = request.GET['reboot_required'] == 'true'
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

    page_no = request.GET.get('page')
    paginator = Paginator(hosts, 50)

    try:
        page = paginator.page(page_no)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    filter_list = []
    tags = {}
    for tag in Tag.objects.all():
        tags[tag.name] = tag.name
    filter_list.append(Filter(request, 'Tag', 'tag', tags))
    filter_list.append(Filter(request, 'Domain', 'domain_id', Domain.objects.all()))
    filter_list.append(Filter(request, 'OS Release', 'osrelease_id',
                              OSRelease.objects.filter(osvariant__host__in=hosts)))
    filter_list.append(Filter(request, 'OS Variant', 'osvariant_id', OSVariant.objects.filter(host__in=hosts)))
    filter_list.append(Filter(request, 'Architecture', 'arch_id', MachineArchitecture.objects.filter(host__in=hosts)))
    filter_list.append(Filter(request, 'Reboot Required', 'reboot_required', {'true': 'Yes', 'false': 'No'}))
    filter_bar = FilterBar(request, filter_list)

    return render(request,
                  'hosts/host_list.html',
                  {'page': page,
                   'filter_bar': filter_bar,
                   'terms': terms})


@login_required
def host_detail(request, hostname):
    host = get_object_or_404(Host, hostname=hostname)
    reports = Report.objects.filter(host=hostname).order_by('-created')[:3]
    hostrepos = HostRepo.objects.filter(host=host)
    return render(request,
                  'hosts/host_detail.html',
                  {'host': host,
                   'reports': reports,
                   'hostrepos': hostrepos})


@login_required
def host_edit(request, hostname):
    host = get_object_or_404(Host, hostname=hostname)
    reports = Report.objects.filter(host=hostname).order_by('-created')[:3]

    if request.method == 'POST':
        if 'save' in request.POST:
            edit_form = EditHostForm(request.POST, instance=host)
            if edit_form.is_valid():
                host = edit_form.save()
                host.save()
                text = f'Saved changes to Host {host}'
                messages.info(request, text)
                return redirect(host.get_absolute_url())
            else:
                host = get_object_or_404(Host, hostname=hostname)
        elif 'cancel' in request.POST:
            return redirect(host.get_absolute_url())
    else:
        edit_form = EditHostForm(instance=host)

    return render(request,
                  'hosts/host_edit.html',
                  {'host': host,
                   'reports': reports,
                   'edit_form': edit_form})


@login_required
def host_delete(request, hostname):
    host = get_object_or_404(Host, hostname=hostname)

    if request.method == 'POST':
        if 'delete' in request.POST:
            host.delete()
            text = f'Host {hostname} has been deleted'
            messages.info(request, text)
            return redirect(reverse('hosts:host_list'))
        elif 'cancel' in request.POST:
            return redirect(host.get_absolute_url())
    reports = Report.objects.filter(host=hostname).order_by('-created')[:3]

    return render(request,
                  'hosts/host_delete.html',
                  {'host': host,
                   'reports': reports})


@login_required
def host_find_updates(request, hostname):
    """ Find updates using a celery task
    """
    from hosts.tasks import find_host_updates
    host = get_object_or_404(Host, hostname=hostname)
    find_host_updates.delay(host.id)
    text = f'Finding updates for Host {host}'
    messages.info(request, text)
    return redirect(host.get_absolute_url())


class HostViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows hosts to be viewed or edited.
    """
    queryset = Host.objects.all()
    serializer_class = HostSerializer
    filterset_fields = ['hostname']


class HostRepoViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows host repos to be viewed or edited.
    """
    queryset = HostRepo.objects.all()
    serializer_class = HostRepoSerializer
