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

from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

from rest_framework import viewsets

from util.filterspecs import Filter, FilterBar
from packages.models import PackageName, Package, PackageUpdate
from arch.models import PackageArchitecture
from packages.serializers import PackageNameSerializer, PackageSerializer, PackageUpdateSerializer


@login_required
def package_list(request):
    packages = Package.objects.select_related()

    if 'arch' in request.GET:
        packages = packages.filter(arch=request.GET['arch']).distinct()

    if 'packagetype' in request.GET:
        packages = packages.filter(packagetype=request.GET['packagetype']).distinct()

    if 'erratum_id' in request.GET:
        packages = packages.filter(erratum=request.GET['erratum_id']).distinct()

    if 'host' in request.GET:
        packages = packages.filter(host__hostname=request.GET['host']).distinct()

    if 'cve_id' in request.GET:
        packages = packages.filter(erratum__cves__cve_id=request.GET['cve_id']).distinct()

    if 'mirror_id' in request.GET:
        packages = packages.filter(mirror=request.GET['mirror_id']).distinct()

    if 'module_id' in request.GET:
        packages = packages.filter(module=request.GET['module_id']).distinct()

    if 'affected_by_errata' in request.GET:
        affected_by_errata = request.GET['affected_by_errata'] == 'True'
        if affected_by_errata:
            packages = packages.filter(erratum__isnull=False)
        else:
            packages = packages.filter(erratum__isnull=True)

    if 'installed_on_hosts' in request.GET:
        installed_on_hosts = request.GET['installed_on_hosts'] == 'True'
        if installed_on_hosts:
            packages = packages.filter(host__isnull=False)
        else:
            packages = packages.filter(host__isnull=True)

    if 'available_in_repos' in request.GET:
        available_in_repos = request.GET['available_in_repos'] == 'True'
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

    page_no = request.GET.get('page')
    paginator = Paginator(packages, 50)

    try:
        page = paginator.page(page_no)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    filter_list = []
    filter_list.append(Filter(request, 'Affected by Errata', 'affected_by_errata', {False: 'No', True: 'Yes'}))
    filter_list.append(Filter(request, 'Installed on Hosts', 'installed_on_hosts', {False: 'No', True: 'Yes'}))
    filter_list.append(Filter(request, 'Available in Repos', 'available_in_repos', {False: 'No', True: 'Yes'}))
    filter_list.append(Filter(request, 'Package Type', 'packagetype', Package.PACKAGE_TYPES))
    filter_list.append(Filter(request, 'Architecture', 'arch', PackageArchitecture.objects.all()))
    filter_bar = FilterBar(request, filter_list)

    return render(request,
                  'packages/package_list.html',
                  {'page': page,
                   'filter_bar': filter_bar,
                   'terms': terms})


@login_required
def package_name_list(request):
    packages = PackageName.objects.select_related()

    if 'arch' in request.GET:
        packages = packages.filter(
            package__arch=int(request.GET['arch'])).distinct()

    if 'packagetype' in request.GET:
        packages = packages.filter(
            package__packagetype=request.GET['packagetype']).distinct()

    if 'search' in request.GET:
        terms = request.GET['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(name__icontains=term)
            query = query & q
        packages = packages.filter(query)
    else:
        terms = ''

    page_no = request.GET.get('page')
    paginator = Paginator(packages, 50)

    try:
        page = paginator.page(page_no)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    filter_list = []
    filter_list.append(Filter(request, 'Package Type', 'packagetype', Package.PACKAGE_TYPES))
    filter_list.append(Filter(request, 'Architecture', 'arch', PackageArchitecture.objects.all()))
    filter_bar = FilterBar(request, filter_list)

    return render(request,
                  'packages/package_name_list.html',
                  {'page': page,
                   'filter_bar': filter_bar,
                   'terms': terms,
                   'table_template': 'packages/package_name_table.html'})


@login_required
def package_detail(request, package_id):
    package = get_object_or_404(Package, id=package_id)
    return render(request,
                  'packages/package_detail.html',
                  {'package': package})


@login_required
def package_name_detail(request, packagename):
    package = get_object_or_404(PackageName, name=packagename)
    allversions = Package.objects.select_related().filter(name=package.id)
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
    queryset = Package.objects.all()
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
    queryset = PackageUpdate.objects.all()
    serializer_class = PackageUpdateSerializer
    filterset_fields = ['oldpackage', 'newpackage', 'security']
