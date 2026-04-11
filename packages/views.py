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

from urllib.parse import parse_qs

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django_tables2 import RequestConfig
from rest_framework import viewsets

from arch.models import PackageArchitecture
from packages.models import Package, PackageName, PackageUpdate
from packages.serializers import (
    PackageNameSerializer, PackageSerializer, PackageUpdateSerializer,
)
from packages.tables import PackageNameTable, PackageTable, PackageUpdateTable
from util import sanitize_filter_params
from util.filterspecs import Filter, FilterBar


def _get_filtered_packages(filter_params):
    """Helper to reconstruct filtered queryset from filter params."""
    params = parse_qs(filter_params)
    packages = Package.objects.select_related('name', 'arch')

    if 'arch_id' in params:
        packages = packages.filter(arch=params['arch_id'][0]).distinct()
    if 'packagetype' in params:
        packages = packages.filter(packagetype=params['packagetype'][0]).distinct()
    if 'affected_by_errata' in params:
        if params['affected_by_errata'][0] == 'true':
            packages = packages.filter(affected_by_erratum__isnull=False)
        else:
            packages = packages.filter(affected_by_erratum__isnull=True)
    if 'provides_fix_in_erratum' in params:
        if params['provides_fix_in_erratum'][0] == 'true':
            packages = packages.filter(provides_fix_in_erratum__isnull=False)
        else:
            packages = packages.filter(provides_fix_in_erratum__isnull=True)
    if 'installed_on_hosts' in params:
        if params['installed_on_hosts'][0] == 'true':
            packages = packages.filter(host__isnull=False)
        else:
            packages = packages.filter(host__isnull=True)
    if 'available_in_repos' in params:
        if params['available_in_repos'][0] == 'true':
            packages = packages.filter(mirror__isnull=False)
        else:
            packages = packages.filter(mirror__isnull=True)
    if 'search' in params:
        terms = params['search'][0].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(name__name__icontains=term)
            query = query & q
        packages = packages.filter(query)

    return packages.distinct()


def _get_filtered_package_updates(filter_params):
    """Helper to reconstruct filtered queryset from filter params."""
    params = parse_qs(filter_params)
    updates = PackageUpdate.objects.select_related(
        'oldpackage__name', 'oldpackage__arch',
        'newpackage__name', 'newpackage__arch',
    )

    if 'security' in params:
        security = params['security'][0] == 'true'
        updates = updates.filter(security=security)
    if 'host_id' in params:
        updates = updates.filter(host=params['host_id'][0])
    if 'search' in params:
        terms = params['search'][0].lower()
        query = Q()
        for term in terms.split(' '):
            q = (Q(oldpackage__name__name__icontains=term) |
                 Q(newpackage__name__name__icontains=term))
            query = query & q
        updates = updates.filter(query)

    return updates.distinct()


@login_required
def package_list(request):
    packages = Package.objects.select_related('name', 'arch')

    if 'arch_id' in request.GET:
        packages = packages.filter(arch=request.GET['arch_id']).distinct()

    if 'packagetype' in request.GET:
        packages = packages.filter(packagetype=request.GET['packagetype']).distinct()

    if 'erratum_id' in request.GET:
        if request.GET['type'] == 'affected':
            packages = packages.filter(affected_by_erratum=request.GET['erratum_id']).distinct()
        elif request.GET['type'] == 'fixed':
            packages = packages.filter(provides_fix_in_erratum=request.GET['erratum_id']).distinct()

    if 'host' in request.GET:
        packages = packages.filter(host__hostname=request.GET['host']).distinct()

    if 'cve_id' in request.GET:
        if request.GET['type'] == 'affected':
            packages = packages.filter(affected_by_erratum__cves__cve_id=request.GET['cve_id']).distinct()
        elif request.GET['type'] == 'fixed':
            packages = packages.filter(provides_fix_in_erratum__cves__cve_id=request.GET['cve_id']).distinct()

    if 'mirror_id' in request.GET:
        packages = packages.filter(mirror=request.GET['mirror_id']).distinct()

    if 'module_id' in request.GET:
        packages = packages.filter(module=request.GET['module_id']).distinct()

    if 'affected_by_errata' in request.GET:
        affected_by_errata = request.GET['affected_by_errata'] == 'true'
        if affected_by_errata:
            packages = packages.filter(affected_by_erratum__isnull=False)
        else:
            packages = packages.filter(affected_by_erratum__isnull=True)

    if 'provides_fix_in_erratum' in request.GET:
        provides_fix_in_erratum = request.GET['provides_fix_in_erratum'] == 'true'
        if provides_fix_in_erratum:
            packages = packages.filter(provides_fix_in_erratum__isnull=False)
        else:
            packages = packages.filter(provides_fix_in_erratum__isnull=True)

    if 'installed_on_hosts' in request.GET:
        installed_on_hosts = request.GET['installed_on_hosts'] == 'true'
        if installed_on_hosts:
            packages = packages.filter(host__isnull=False)
        else:
            packages = packages.filter(host__isnull=True)

    if 'available_in_repos' in request.GET:
        available_in_repos = request.GET['available_in_repos'] == 'true'
        if available_in_repos:
            packages = packages.filter(mirror__isnull=False)
        else:
            packages = packages.filter(mirror__isnull=True)

    if 'search' in request.GET:
        terms = request.GET['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(name__name__icontains=term)
            query = query & q
        packages = packages.filter(query)
    else:
        terms = ''

    filter_list = []
    filter_list.append(Filter(request, 'Affected by Errata', 'affected_by_errata', {'true': 'Yes', 'false': 'No'}))
    filter_list.append(Filter(request, 'Provides Fix in Errata', 'provides_fix_in_erratum',
                              {'true': 'Yes', 'false': 'No'}))
    filter_list.append(Filter(request, 'Installed on Hosts', 'installed_on_hosts', {'true': 'Yes', 'false': 'No'}))
    filter_list.append(Filter(request, 'Available in Repos', 'available_in_repos', {'true': 'Yes', 'false': 'No'}))
    filter_list.append(Filter(request, 'Package Type', 'packagetype', Package.PACKAGE_TYPES))
    filter_list.append(Filter(request, 'Architecture', 'arch_id', PackageArchitecture.objects.all()))
    filter_bar = FilterBar(request, filter_list)

    packages = packages.annotate(
        host_count=Count('host', distinct=True),
        repo_count=Count('mirror__repo', distinct=True),
        affected_count=Count('affected_by_erratum', distinct=True),
        fixed_count=Count('provides_fix_in_erratum', distinct=True),
    )

    table = PackageTable(packages)
    RequestConfig(request, paginate={'per_page': 50}).configure(table)

    filter_params = sanitize_filter_params(request.GET.urlencode())
    bulk_actions = [
        {'value': 'delete', 'label': 'Delete'},
    ]

    return render(request,
                  'packages/package_list.html',
                  {'table': table,
                   'filter_bar': filter_bar,
                   'terms': terms,
                   'total_count': packages.count(),
                   'filter_params': filter_params,
                   'bulk_actions': bulk_actions})


@login_required
def package_name_list(request):
    packages = PackageName.objects.all()

    if 'arch_id' in request.GET:
        packages = packages.filter(package__arch=request.GET['arch_id']).distinct()

    if 'packagetype' in request.GET:
        packages = packages.filter(package__packagetype=request.GET['packagetype']).distinct()

    if 'search' in request.GET:
        terms = request.GET['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(name__icontains=term)
            query = query & q
        packages = packages.filter(query)
    else:
        terms = ''

    filter_list = []
    filter_list.append(Filter(request, 'Package Type', 'packagetype', Package.PACKAGE_TYPES))
    filter_list.append(Filter(request, 'Architecture', 'arch_id', PackageArchitecture.objects.all()))
    filter_bar = FilterBar(request, filter_list)

    packages = packages.annotate(host_count=Count('package__host', distinct=True))

    table = PackageNameTable(packages)
    RequestConfig(request, paginate={'per_page': 50}).configure(table)

    return render(request,
                  'packages/package_name_list.html',
                  {'table': table,
                   'filter_bar': filter_bar,
                   'terms': terms})


@login_required
def package_detail(request, package_id):
    package = get_object_or_404(Package, id=package_id)
    return render(request,
                  'packages/package_detail.html',
                  {'package': package})


@login_required
def package_name_detail(request, packagename):
    package = get_object_or_404(PackageName, name=packagename)
    allversions = Package.objects.select_related(
        'name', 'arch',
    ).filter(name=package.id).annotate(
        host_count=Count('host', distinct=True),
        repo_count=Count('mirror__repo', distinct=True),
        affected_count=Count('affected_by_erratum', distinct=True),
        fixed_count=Count('provides_fix_in_erratum', distinct=True),
    )
    table = PackageTable(allversions)
    RequestConfig(request, paginate={'per_page': 50}).configure(table)
    return render(request,
                  'packages/package_name_detail.html',
                  {'package': package,
                   'table': table})


@login_required
def package_update_list(request):
    updates = PackageUpdate.objects.select_related(
        'oldpackage__name', 'oldpackage__arch',
        'newpackage__name', 'newpackage__arch',
    ).annotate(
        host_count=Count('host', distinct=True),
        affected_count=Count('oldpackage__affected_by_erratum', distinct=True),
        fixed_count=Count('newpackage__provides_fix_in_erratum', distinct=True),
    )

    if 'security' in request.GET:
        security = request.GET['security'] == 'true'
        updates = updates.filter(security=security)
    if 'host_id' in request.GET:
        updates = updates.filter(host=request.GET['host_id'])
    if 'search' in request.GET:
        terms = request.GET['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = (Q(oldpackage__name__name__icontains=term) |
                 Q(newpackage__name__name__icontains=term))
            query = query & q
        updates = updates.filter(query)
    else:
        terms = ''

    filter_list = []
    filter_list.append(Filter(request, 'Type', 'security',
                              {'true': 'Security', 'false': 'Bugfix'}))
    filter_bar = FilterBar(request, filter_list)

    table = PackageUpdateTable(updates.distinct())
    RequestConfig(request, paginate={'per_page': 50}).configure(table)

    filter_params = sanitize_filter_params(request.GET.urlencode())
    bulk_actions = [
        {'value': 'delete', 'label': 'Delete'},
    ]

    return render(request,
                  'packages/package_update_list.html',
                  {'table': table,
                   'filter_bar': filter_bar,
                   'terms': terms,
                   'total_count': updates.distinct().count(),
                   'filter_params': filter_params,
                   'bulk_actions': bulk_actions})


@login_required
def package_bulk_action(request):
    """Handle bulk actions on packages."""
    if request.method != 'POST':
        return redirect('packages:package_list')

    action = request.POST.get('action', '')
    select_all_filtered = request.POST.get('select_all_filtered') == '1'
    filter_params = sanitize_filter_params(request.POST.get('filter_params', ''))

    if not action:
        messages.warning(request, 'Please select an action')
        if filter_params:
            return redirect(f"{reverse('packages:package_list')}?{filter_params}")
        return redirect('packages:package_list')

    if select_all_filtered:
        packages = _get_filtered_packages(filter_params)
    else:
        selected_ids = request.POST.getlist('selected_ids')
        if not selected_ids:
            messages.warning(request, 'No packages selected')
            if filter_params:
                return redirect(f"{reverse('packages:package_list')}?{filter_params}")
            return redirect('packages:package_list')
        packages = Package.objects.filter(id__in=selected_ids)

    count = packages.count()
    name = Package._meta.verbose_name if count == 1 else Package._meta.verbose_name_plural

    if action == 'delete':
        packages.delete()
        messages.success(request, f'Deleted {count} {name}')
    else:
        messages.warning(request, 'Invalid action')

    if filter_params:
        return redirect(f"{reverse('packages:package_list')}?{filter_params}")
    return redirect('packages:package_list')


@login_required
def package_update_bulk_action(request):
    """Handle bulk actions on package updates."""
    if request.method != 'POST':
        return redirect('packages:package_update_list')

    action = request.POST.get('action', '')
    select_all_filtered = request.POST.get('select_all_filtered') == '1'
    filter_params = sanitize_filter_params(request.POST.get('filter_params', ''))

    if not action:
        messages.warning(request, 'Please select an action')
        if filter_params:
            return redirect(f"{reverse('packages:package_update_list')}?{filter_params}")
        return redirect('packages:package_update_list')

    if select_all_filtered:
        updates = _get_filtered_package_updates(filter_params)
    else:
        selected_ids = request.POST.getlist('selected_ids')
        if not selected_ids:
            messages.warning(request, 'No package updates selected')
            if filter_params:
                return redirect(f"{reverse('packages:package_update_list')}?{filter_params}")
            return redirect('packages:package_update_list')
        updates = PackageUpdate.objects.filter(id__in=selected_ids)

    count = updates.count()
    name = PackageUpdate._meta.verbose_name if count == 1 else PackageUpdate._meta.verbose_name_plural

    if action == 'delete':
        updates.delete()
        messages.success(request, f'Deleted {count} {name}')
    else:
        messages.warning(request, 'Invalid action')

    if filter_params:
        return redirect(f"{reverse('packages:package_update_list')}?{filter_params}")
    return redirect('packages:package_update_list')


class PackageNameViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows package names to be viewed or edited.
    """
    queryset = PackageName.objects.all()
    serializer_class = PackageNameSerializer
    filterset_fields = ['name']


class PackageViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows packages to be viewed or edited.
    """
    queryset = Package.objects.select_related('name', 'arch').all()
    serializer_class = PackageSerializer
    filterset_fields = [
        'name',
        'epoch',
        'version',
        'release',
        'arch',
        'packagetype'
    ]


class PackageUpdateViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows packages updates to be viewed or edited.
    """
    queryset = PackageUpdate.objects.select_related('oldpackage', 'newpackage').all()
    serializer_class = PackageUpdateSerializer
    filterset_fields = ['oldpackage', 'newpackage', 'security']
