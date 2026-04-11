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
from urllib.parse import parse_qs

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse
from django_filters import rest_framework as filters
from django_tables2 import RequestConfig
from rest_framework import viewsets
from taggit.models import Tag

from arch.models import MachineArchitecture
from domains.models import Domain
from hosts.forms import EditHostForm
from hosts.models import Host, HostRepo
from hosts.serializers import HostRepoSerializer, HostSerializer
from hosts.tables import HostTable
from hosts.tasks import find_host_updates
from operatingsystems.models import OSRelease, OSVariant
from reports.models import Report
from util import get_setting_of_type, sanitize_filter_params
from util.filterspecs import Filter, FilterBar


def _get_filtered_hosts(filter_params):
    """Helper to reconstruct filtered queryset from filter params."""
    params = parse_qs(filter_params)

    hosts = Host.objects.select_related('osvariant', 'arch', 'domain')

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
    if 'stale' in params:
        days = get_setting_of_type(
            setting_name='DAYS_WITHOUT_REPORT',
            setting_type=int,
            default=14,
        )
        stale = params['stale'][0] == 'true'
        last_report_delta = timezone.now() - timedelta(days=days)
        if stale:
            hosts = hosts.filter(lastreport__lt=last_report_delta)
        else:
            hosts = hosts.filter(lastreport__gte=last_report_delta)
    if 'has_security_updates' in params:
        has_security_updates = params['has_security_updates'][0] == 'true'
        if has_security_updates:
            hosts = hosts.filter(sec_updates_count__gt=0)
        else:
            hosts = hosts.filter(sec_updates_count=0)
    if 'has_bugfix_updates' in params:
        has_bugfix_updates = params['has_bugfix_updates'][0] == 'true'
        if has_bugfix_updates:
            hosts = hosts.filter(bug_updates_count__gt=0)
        else:
            hosts = hosts.filter(bug_updates_count=0)
    if 'has_repos' in params:
        has_repos = params['has_repos'][0] == 'true'
        if has_repos:
            hosts = hosts.exclude(repos__isnull=True, osvariant__osrelease__repos__isnull=True)
        else:
            hosts = hosts.filter(repos__isnull=True, osvariant__osrelease__repos__isnull=True)
    if 'rdns_mismatch' in params:
        rdns_mismatch = params['rdns_mismatch'][0] == 'true'
        if rdns_mismatch:
            hosts = hosts.exclude(reversedns=F('hostname')).filter(check_dns=True)
        else:
            hosts = hosts.filter(reversedns=F('hostname'))
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
    # Use cached count fields instead of expensive annotations
    hosts = Host.objects.select_related('osvariant', 'arch', 'domain')

    if 'domain_id' in request.GET:
        hosts = hosts.filter(domain=request.GET['domain_id'])

    if 'package_id' in request.GET:
        hosts = hosts.filter(packages=request.GET['package_id'])

    if 'package' in request.GET:
        hosts = hosts.filter(packages__name__name=request.GET['package'])

    if 'update_id' in request.GET:
        hosts = hosts.filter(updates=request.GET['update_id'])

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

    if 'stale' in request.GET:
        days = get_setting_of_type(
            setting_name='DAYS_WITHOUT_REPORT',
            setting_type=int,
            default=14,
        )
        stale = request.GET['stale'] == 'true'
        last_report_delta = timezone.now() - timedelta(days=days)
        if stale:
            hosts = hosts.filter(lastreport__lt=last_report_delta)
        else:
            hosts = hosts.filter(lastreport__gte=last_report_delta)

    if 'has_security_updates' in request.GET:
        has_security_updates = request.GET['has_security_updates'] == 'true'
        if has_security_updates:
            hosts = hosts.filter(sec_updates_count__gt=0)
        else:
            hosts = hosts.filter(sec_updates_count=0)

    if 'has_bugfix_updates' in request.GET:
        has_bugfix_updates = request.GET['has_bugfix_updates'] == 'true'
        if has_bugfix_updates:
            hosts = hosts.filter(bug_updates_count__gt=0)
        else:
            hosts = hosts.filter(bug_updates_count=0)

    if 'has_repos' in request.GET:
        has_repos = request.GET['has_repos'] == 'true'
        if has_repos:
            hosts = hosts.exclude(repos__isnull=True, osvariant__osrelease__repos__isnull=True)
        else:
            hosts = hosts.filter(repos__isnull=True, osvariant__osrelease__repos__isnull=True)

    if 'rdns_mismatch' in request.GET:
        rdns_mismatch = request.GET['rdns_mismatch'] == 'true'
        if rdns_mismatch:
            hosts = hosts.exclude(reversedns=F('hostname')).filter(check_dns=True)
        else:
            hosts = hosts.filter(reversedns=F('hostname'))

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
    filter_list.append(Filter(request, 'Stale', 'stale', {'true': 'Yes', 'false': 'No'}))
    filter_list.append(Filter(request, 'Security Updates', 'has_security_updates', {'true': 'Yes', 'false': 'No'}))
    filter_list.append(Filter(request, 'Bugfix Updates', 'has_bugfix_updates', {'true': 'Yes', 'false': 'No'}))
    filter_list.append(Filter(request, 'Has Repos', 'has_repos', {'true': 'Yes', 'false': 'No'}))
    filter_list.append(Filter(request, 'rDNS Mismatch', 'rdns_mismatch', {'true': 'Yes', 'false': 'No'}))
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

    # Build packages list with update info
    updates_by_package = {u.oldpackage_id: u for u in host.updates.select_related('oldpackage', 'newpackage')}
    packages_with_updates = []
    for package in host.packages.select_related('name', 'arch').order_by('name__name'):
        package.update = updates_by_package.get(package.id)
        packages_with_updates.append(package)

    return render(request,
                  'hosts/host_detail.html',
                  {'host': host,
                   'reports': reports,
                   'hostrepos': hostrepos,
                   'packages_with_updates': packages_with_updates})


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


class HostFilter(filters.FilterSet):
    package_id = filters.NumberFilter(field_name='packages', lookup_expr='exact')
    package_name = filters.CharFilter(field_name='packages__name__name', lookup_expr='exact')
    package_version = filters.CharFilter(field_name='packages__version', lookup_expr='exact')
    package_release = filters.CharFilter(field_name='packages__release', lookup_expr='exact')
    package_epoch = filters.CharFilter(field_name='packages__epoch', lookup_expr='exact')
    package_arch = filters.CharFilter(field_name='packages__arch__name', lookup_expr='exact')
    tag = filters.CharFilter(field_name='tags__name', lookup_expr='exact')

    class Meta:
        model = Host
        fields = ['hostname']


class HostViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows hosts to be viewed or edited.
    """
    queryset = Host.objects.select_related('osvariant', 'arch', 'domain').all()
    serializer_class = HostSerializer
    filterset_class = HostFilter


class HostRepoViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows host repos to be viewed or edited.
    """
    queryset = HostRepo.objects.select_related('host', 'repo').all()
    serializer_class = HostRepoSerializer
