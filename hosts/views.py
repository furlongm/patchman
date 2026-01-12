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
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django_tables2 import RequestConfig
from rest_framework import viewsets
from taggit.models import Tag

from arch.models import MachineArchitecture
from domains.models import Domain
from hosts.forms import EditHostForm
from hosts.models import Host, HostRepo
from hosts.serializers import HostRepoSerializer, HostSerializer
from hosts.tables import HostTable
from operatingsystems.models import OSRelease, OSVariant
from reports.models import Report
from util import sanitize_filter_params
from util.filterspecs import Filter, FilterBar


def _get_filtered_hosts(filter_params):
    """Helper to reconstruct filtered queryset from filter params."""
    from urllib.parse import parse_qs
    params = parse_qs(filter_params)

    hosts = Host.objects.select_related()

    if 'domain_id' in params:
        hosts = hosts.filter(domain=params['domain_id'][0])
    if 'package_id' in params:
        hosts = hosts.filter(packages=params['package_id'][0])
    if 'package' in params:
        hosts = hosts.filter(packages__name__name=params['package'][0])
    if 'repo_id' in params:
        hosts = hosts.filter(repos=params['repo_id'][0])
    if 'arch_id' in params:
        hosts = hosts.filter(arch=params['arch_id'][0])
    if 'osvariant_id' in params:
        hosts = hosts.filter(osvariant=params['osvariant_id'][0])
    if 'osrelease_id' in params:
        hosts = hosts.filter(osvariant__osrelease=params['osrelease_id'][0])
    if 'tag' in params:
        hosts = hosts.filter(tags__name__in=[params['tag'][0]])
    if 'reboot_required' in params:
        reboot_required = params['reboot_required'][0] == 'true'
        hosts = hosts.filter(reboot_required=reboot_required)
    if 'search' in params:
        terms = params['search'][0].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(hostname__icontains=term)
            query = query & q
        hosts = hosts.filter(query)

    return hosts


@login_required
def host_list(request):
    hosts = Host.objects.select_related().annotate(
        sec_updates_count=Count('updates', filter=Q(updates__security=True)),
        bug_updates_count=Count('updates', filter=Q(updates__security=False)),
        errata_count=Count('errata'),
    )

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

    table = HostTable(hosts)
    RequestConfig(request, paginate={'per_page': 50}).configure(table)

    filter_params = sanitize_filter_params(request.GET.urlencode())
    bulk_actions = [
        {'value': 'find_updates', 'label': 'Find Updates'},
        {'value': 'delete', 'label': 'Delete'},
    ]

    return render(request,
                  'hosts/host_list.html',
                  {'table': table,
                   'filter_bar': filter_bar,
                   'terms': terms,
                   'total_count': hosts.count(),
                   'filter_params': filter_params,
                   'bulk_actions': bulk_actions})


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


@login_required
def host_bulk_action(request):
    """Handle bulk actions on hosts."""
    if request.method != 'POST':
        return redirect('hosts:host_list')

    action = request.POST.get('action', '')
    select_all_filtered = request.POST.get('select_all_filtered') == '1'
    filter_params = sanitize_filter_params(request.POST.get('filter_params', ''))

    if not action:
        messages.warning(request, 'Please select an action')
        if filter_params:
            return redirect(f"{reverse('hosts:host_list')}?{filter_params}")
        return redirect('hosts:host_list')

    if select_all_filtered:
        hosts = _get_filtered_hosts(filter_params)
    else:
        selected_ids = request.POST.getlist('selected_ids')
        if not selected_ids:
            messages.warning(request, 'No hosts selected')
            if filter_params:
                return redirect(f"{reverse('hosts:host_list')}?{filter_params}")
            return redirect('hosts:host_list')
        hosts = Host.objects.filter(id__in=selected_ids)

    count = hosts.count()
    name = Host._meta.verbose_name if count == 1 else Host._meta.verbose_name_plural

    if action == 'find_updates':
        from hosts.tasks import find_host_updates
        for host in hosts:
            find_host_updates.delay(host.id)
        messages.success(request, f'Queued {count} {name} for update check')
    elif action == 'delete':
        hosts.delete()
        messages.success(request, f'Deleted {count} {name}')
    else:
        messages.warning(request, 'Invalid action')

    if filter_params:
        return redirect(f"{reverse('hosts:host_list')}?{filter_params}")
    return redirect('hosts:host_list')


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
