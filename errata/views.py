# Copyright 2025 Marcus Furlong <furlongm@gmail.com>
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

from errata.models import Erratum
from errata.serializers import ErratumSerializer
from errata.tables import ErratumTable
from operatingsystems.models import OSRelease
from util.filterspecs import Filter, FilterBar


@login_required
def erratum_list(request):
    errata = Erratum.objects.all()

    if 'e_type' in request.GET:
        errata = errata.filter(e_type=request.GET['e_type']).distinct()

    if 'reference_id' in request.GET:
        errata = errata.filter(references=request.GET['reference_id'])

    if 'cve_id' in request.GET:
        errata = errata.filter(cves__cve_id=request.GET['cve_id'])

    if 'package_id' in request.GET:
        if request.GET['type'] == 'affected':
            errata = errata.filter(affected_packages=request.GET['package_id'])
        elif request.GET['type'] == 'fixed':
            errata = errata.filter(fixed_packages=request.GET['package_id'])

    if 'osrelease_id' in request.GET:
        errata = errata.filter(osreleases=request.GET['osrelease_id'])

    if 'host' in request.GET:
        errata = errata.filter(host__hostname=request.GET['host'])

    if 'search' in request.GET:
        terms = request.GET['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(name__icontains=term) | Q(synopsis__icontains=term)
            query = query & q
        errata = errata.filter(query)
    else:
        terms = ''

    filter_list = []
    filter_list.append(Filter(request, 'Erratum Type', 'e_type',
                              Erratum.objects.values_list('e_type', flat=True).distinct()))
    filter_list.append(Filter(request, 'OS Release', 'osrelease_id',
                              OSRelease.objects.filter(erratum__in=errata)))
    filter_bar = FilterBar(request, filter_list)

    table = ErratumTable(errata)
    RequestConfig(request, paginate={'per_page': 50}).configure(table)

    return render(request,
                  'errata/erratum_list.html',
                  {'table': table,
                   'filter_bar': filter_bar,
                   'terms': terms})


@login_required
def erratum_detail(request, erratum_name):
    erratum = get_object_or_404(Erratum, name=erratum_name)
    return render(request,
                  'errata/erratum_detail.html',
                  {'erratum': erratum})


class ErratumViewSet(viewsets.ModelViewSet):
    """ API endpoint that allows errata to be viewed or edited.
    """
    queryset = Erratum.objects.all()
    serializer_class = ErratumSerializer
