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

from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.contrib import messages
from django.urls import reverse

from rest_framework import viewsets

from hosts.models import Host
from operatingsystems.models import OSVariant, OSRelease
from operatingsystems.forms import AddOSVariantToOSReleaseForm, AddReposToOSReleaseForm, CreateOSReleaseForm
from operatingsystems.serializers import OSVariantSerializer, OSReleaseSerializer


@login_required
def osvariant_list(request):
    osvariants = OSVariant.objects.select_related()

    if 'osrelease_id' in request.GET:
        osvariants = osvariants.filter(osrelease=request.GET['osrelease_id'])

    if 'search' in request.GET:
        terms = request.GET['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(name__icontains=term)
            query = query & q
        osvariants = osvariants.filter(query)
    else:
        terms = ''

    page_no = request.GET.get('page')
    paginator = Paginator(osvariants, 50)

    try:
        page = paginator.page(page_no)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    nohost_osvariants = OSVariant.objects.filter(host__isnull=True).exists()

    return render(request,
                  'operatingsystems/osvariant_list.html',
                  {'page': page,
                   'terms': terms,
                   'nohost_osvariants': nohost_osvariants})


@login_required
def osvariant_detail(request, osvariant_id):
    osvariant = get_object_or_404(OSVariant, id=osvariant_id)

    if request.method == 'POST':
        create_form = CreateOSReleaseForm(request.POST, prefix='create')
        if create_form.is_valid():
            osrelease = create_form.save()
            osvariant.osrelease = osrelease
            osvariant.save()
            text = f'Created OS Release {osrelease} and added OS Variant {osvariant} to it'
            messages.info(request, text)
            return redirect(osvariant.get_absolute_url())
        add_form = AddOSVariantToOSReleaseForm(request.POST, instance=osvariant, prefix='add')
        if add_form.is_valid():
            add_form.save()
            text = f'OS Variant {osvariant} added to OS Release {osvariant.osrelease}'
            messages.info(request, text)
            return redirect(osvariant.get_absolute_url())
    else:
        add_form = AddOSVariantToOSReleaseForm(instance=osvariant, prefix='add')
        create_form = CreateOSReleaseForm(prefix='create')

    return render(request,
                  'operatingsystems/osvariant_detail.html',
                  {'osvariant': osvariant,
                   'add_form': add_form,
                   'create_form': create_form})


@login_required
def osvariant_delete(request, osvariant_id):
    osvariant = get_object_or_404(OSVariant, id=osvariant_id)

    if request.method == 'POST':
        if 'delete' in request.POST:
            osvariant.delete()
            messages.info(request, f'OS Variant {osvariant} has been deleted')
            return redirect(reverse('operatingsystems:osvariant_list'))
        elif 'cancel' in request.POST:
            return redirect(osvariant.get_absolute_url())

    return render(request, 'operatingsystems/osvariant_delete.html', {'osvariant': osvariant})


@login_required
def delete_nohost_osvariants(request):
    osvariants = OSVariant.objects.filter(host__isnull=True)

    if request.method == 'POST':
        if 'delete' in request.POST:
            if not osvariants:
                text = 'There are no OS Variants with no Hosts'
                messages.info(request, text)
                return redirect(reverse('operatingsystems:osvariant_list'))
            text = f'{osvariants.count()} OS Variants have been deleted'
            osvariants.delete()
            messages.info(request, text)
            return redirect(reverse('operatingsystems:osvariant_list'))
        elif 'cancel' in request.POST:
            return redirect(reverse('operatingsystems:osvariant_list'))

    return render(request, 'operatingsystems/osvariant_delete_multiple.html', {'osvariants': osvariants})


@login_required
def osrelease_list(request):
    osreleases = OSRelease.objects.select_related()

    if 'erratum_id' in request.GET:
        osreleases = osreleases.filter(erratum=request.GET['erratum_id'])

    if 'search' in request.GET:
        terms = request.GET['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(name__icontains=term)
            query = query & q
        osreleases = osreleases.filter(query)
    else:
        terms = ''

    page_no = request.GET.get('page')
    paginator = Paginator(osreleases, 50)

    try:
        page = paginator.page(page_no)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    return render(request,
                  'operatingsystems/osrelease_list.html',
                  {'page': page,
                   'terms': terms})


@login_required
def osrelease_detail(request, osrelease_id):
    osrelease = get_object_or_404(OSRelease, id=osrelease_id)

    if request.method == 'POST':
        repos_form = AddReposToOSReleaseForm(request.POST, instance=osrelease)
        if repos_form.is_valid():
            repos_form.save()
            messages.info(request, 'Modified Repositories')
            return redirect(osrelease.get_absolute_url())

    repos_form = AddReposToOSReleaseForm(instance=osrelease)
    host_count = Host.objects.filter(osvariant__osrelease=osrelease).count()

    return render(request,
                  'operatingsystems/osrelease_detail.html',
                  {'osrelease': osrelease,
                   'repos_form': repos_form,
                   'host_count': host_count})


@login_required
def osrelease_delete(request, osrelease_id):
    osrelease = get_object_or_404(OSRelease, id=osrelease_id)

    if request.method == 'POST':
        if 'delete' in request.POST:
            osrelease.delete()
            text = f'OS Release {osrelease} has been deleted'
            messages.info(request, text)
            return redirect(reverse('operatingsystems:osrelease_list'))
        elif 'cancel' in request.POST:
            return redirect(osrelease.get_absolute_url())

    host_count = Host.objects.filter(osvariant__osrelease=osrelease).count()

    return render(request,
                  'operatingsystems/osrelease_delete.html',
                  {'osrelease': osrelease,
                   'host_count': host_count})


@login_required
def os_landing(request):
    return render(request, 'operatingsystems/os_landing.html')


class OSVariantViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows operating system variants to be viewed or edited.
    """
    queryset = OSVariant.objects.all()
    serializer_class = OSVariantSerializer
    filterset_fields = ['name']


class OSReleaseViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows operating system releases to be viewed or edited.
    """
    queryset = OSRelease.objects.all()
    serializer_class = OSReleaseSerializer
    filterset_fields = ['name']
