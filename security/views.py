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

from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

from rest_framework import viewsets

from packages.models import Package
from operatingsystems.models import OSRelease
from security.models import CVE, CWE
from security.serializers import CVESerializer, CWESerializer


@login_required
def cwe_list(request):
    cwes = CWE.objects.select_related()

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

    page_no = request.GET.get('page')
    paginator = Paginator(cwes, 50)

    try:
        page = paginator.page(page_no)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    return render(request,
                  'security/cwe_list.html',
                  {'page': page,
                   'terms': terms})


@login_required
def cwe_detail(request, cwe_id):
    cwe = get_object_or_404(CWE, cwe_id=cwe_id)
    return render(request,
                  'security/cwe_detail.html',
                  {'cwe': cwe})


@login_required
def cve_list(request):
    cves = CVE.objects.select_related()

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

    page_no = request.GET.get('page')
    paginator = Paginator(cves, 50)

    try:
        page = paginator.page(page_no)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    return render(request,
                  'security/cve_list.html',
                  {'page': page,
                   'terms': terms})


@login_required
def cve_detail(request, cve_id):
    cve = get_object_or_404(CVE, cve_id=cve_id)
    packages = Package.objects.filter(erratum__in=cve.erratum_set.all()).distinct()
    osreleases = OSRelease.objects.filter(erratum__in=cve.erratum_set.all()).distinct()
    return render(request,
                  'security/cve_detail.html',
                  {'cve': cve,
                   'packages': packages,
                   'osreleases': osreleases})


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
