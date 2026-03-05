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

from operatingsystems.models import OSRelease
from packages.models import Package
from security.models import CVE, CWE, Reference
from security.serializers import (
    CVESerializer, CWESerializer, ReferenceSerializer,
)
from security.tables import CVETable, CWETable, ReferenceTable
from util.filterspecs import Filter, FilterBar


@login_required
def cwe_list(request):
    cwes = CWE.objects.all()

    if 'search' in request.GET:
        terms = request.GET['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(cwe_id__icontains=term) | \
                Q(name__icontains=term) | \
                Q(description__icontains=term)
            query = query & q
        cwes = cwes.filter(query)
    else:
        terms = ''

    table = CWETable(cwes)
    RequestConfig(request, paginate={'per_page': 50}).configure(table)

    return render(request,
                  'security/cwe_list.html',
                  {'table': table,
                   'terms': terms})


@login_required
def cwe_detail(request, cwe_id):
    cwe = get_object_or_404(CWE, cwe_id=cwe_id)
    return render(request,
                  'security/cwe_detail.html',
                  {'cwe': cwe})


@login_required
def cve_list(request):
    cves = CVE.objects.all()

    if 'erratum_id' in request.GET:
        cves = cves.filter(erratum=request.GET['erratum_id'])

    if 'reference_id' in request.GET:
        cves = cves.filter(references=request.GET['reference_id'])

    if 'package_id' in request.GET:
        cves = cves.filter(packages=request.GET['package_id'])

    if 'cwe_id' in request.GET:
        cves = cves.filter(cwes__cwe_id=request.GET['cwe_id'])

    if 'search' in request.GET:
        terms = request.GET['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(cve_id__icontains=term)
            query = query & q
        cves = cves.filter(query)
    else:
        terms = ''

    table = CVETable(cves)
    RequestConfig(request, paginate={'per_page': 50}).configure(table)

    return render(request,
                  'security/cve_list.html',
                  {'table': table,
                   'terms': terms})


@login_required
def cve_detail(request, cve_id):
    cve = get_object_or_404(CVE, cve_id=cve_id)
    affected_packages = Package.objects.filter(affected_by_erratum__in=cve.erratum_set.all()).distinct()
    fixed_packages = Package.objects.filter(provides_fix_in_erratum__in=cve.erratum_set.all()).distinct()
    osreleases = OSRelease.objects.filter(erratum__in=cve.erratum_set.all()).distinct()
    references = Reference.objects.filter(Q(erratum__in=cve.erratum_set.all()) | Q(cve=cve)).distinct()
    return render(request,
                  'security/cve_detail.html',
                  {'cve': cve,
                   'affected_packages': affected_packages,
                   'fixed_packages': fixed_packages,
                   'osreleases': osreleases,
                   'references': references,
                   })


@login_required
def reference_list(request):
    refs = Reference.objects.all().order_by('ref_type')

    if 'ref_type' in request.GET:
        refs = refs.filter(ref_type=request.GET['ref_type']).distinct()

    if 'erratum_id' in request.GET:
        refs = refs.filter(erratum__id=request.GET['erratum_id'])

    if 'search' in request.GET:
        terms = request.GET['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(url__icontains=term)
            query = query & q
        refs = refs.filter(query)
    else:
        terms = ''

    filter_list = []
    filter_list.append(Filter(request, 'Reference Type', 'ref_type',
                              Reference.objects.values_list('ref_type', flat=True).distinct()))
    filter_bar = FilterBar(request, filter_list)

    table = ReferenceTable(refs)
    RequestConfig(request, paginate={'per_page': 50}).configure(table)

    return render(request,
                  'security/reference_list.html',
                  {'table': table,
                   'filter_bar': filter_bar,
                   'terms': terms})


@login_required
def security_landing(request):
    return render(request, 'security/security_landing.html')


class CWEViewSet(viewsets.ModelViewSet):
    """ API endpoint that allows CWEs to be viewed or edited.
    """
    queryset = CWE.objects.all()
    serializer_class = CWESerializer


class CVEViewSet(viewsets.ModelViewSet):
    """ API endpoint that allows CVEs to be viewed or edited.
    """
    queryset = CVE.objects.all()
    serializer_class = CVESerializer


class ReferenceViewSet(viewsets.ModelViewSet):
    """ API endpoint that allows security references to be viewed or edited.
    """
    queryset = Reference.objects.all()
    serializer_class = ReferenceSerializer
