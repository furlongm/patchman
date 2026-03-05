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

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django_tables2 import RequestConfig
from rest_framework import viewsets

from arch.models import PackageArchitecture
from packages.models import Package, PackageName, PackageUpdate
from packages.serializers import (
    PackageNameSerializer, PackageSerializer, PackageUpdateSerializer,
)
from packages.tables import PackageNameTable, PackageTable
from util.filterspecs import Filter, FilterBar


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

    table = PackageTable(packages)
    RequestConfig(request, paginate={'per_page': 50}).configure(table)

    return render(request,
                  'packages/package_list.html',
                  {'table': table,
                   'filter_bar': filter_bar,
                   'terms': terms})


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
    allversions = Package.objects.select_related('name', 'arch').filter(name=package.id)
    return render(request,
                  'packages/package_name_detail.html',
                  {'package': package,
                   'allversions': allversions})


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
