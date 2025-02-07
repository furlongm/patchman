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

from util.filterspecs import Filter, FilterBar
from errata.models import Erratum, ErratumReference
from errata.serializers import ErratumSerializer, ErratumReferenceSerializer


@login_required
def erratum_list(request):
    errata = Erratum.objects.select_related()

    if 'e_type' in request.GET:
        errata = errata.filter(e_type=request.GET['e_type']).distinct()

    if 'reference_id' in request.GET:
        errata = errata.filter(references=int(request.GET['reference_id']))

    if 'cve_id' in request.GET:
        errata = errata.filter(cves__cve_id=request.GET['cve_id'])

    if 'package_id' in request.GET:
        errata = errata.filter(packages=int(request.GET['package_id']))

    if 'search' in request.GET:
        terms = request.GET['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(name__icontains=term) | Q(synopsis__icontains=term)
            query = query & q
        errata = errata.filter(query)
    else:
        terms = ''

    page_no = request.GET.get('page')
    paginator = Paginator(errata, 50)

    try:
        page = paginator.page(page_no)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    filter_list = []
    filter_list.append(Filter(request, 'Erratum Type', 'e_type',
                              Erratum.objects.values_list('e_type', flat=True).distinct()))
    filter_bar = FilterBar(request, filter_list)

    return render(request,
                  'errata/erratum_list.html',
                  {'page': page,
                   'filter_bar': filter_bar,
                   'terms': terms})


@login_required
def erratumreference_list(request):
    erefs = ErratumReference.objects.select_related()

    if 'er_type' in request.GET:
        erefs = erefs.filter(er_type=request.GET['er_type']).distinct()

    if 'erratum_id' in request.GET:
        erefs = erefs.filter(erratum__id=int(request.GET['erratum_id']))

    if 'search' in request.GET:
        terms = request.GET['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(url__icontains=term)
            query = query & q
        erefs = erefs.filter(query)
    else:
        terms = ''

    page_no = request.GET.get('page')
    paginator = Paginator(erefs, 50)

    try:
        page = paginator.page(page_no)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    filter_list = []
    filter_list.append(Filter(request, 'Reference Type', 'er_type',
                              ErratumReference.objects.values_list('er_type', flat=True).distinct()))
    filter_bar = FilterBar(request, filter_list)

    return render(request,
                  'errata/erratumreference_list.html',
                  {'page': page,
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


class ErratumReferenceViewSet(viewsets.ModelViewSet):
    """ API endpoint that allows erratum references to be viewed or edited.
    """
    queryset = ErratumReference.objects.all()
    serializer_class = ErratumReferenceSerializer
