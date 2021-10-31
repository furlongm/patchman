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

from rest_framework import viewsets, permissions

from operatingsystems.models import OS, OSGroup
from operatingsystems.forms import AddOSToOSGroupForm, \
    AddReposToOSGroupForm, CreateOSGroupForm
from operatingsystems.serializers import OSSerializer, \
    OSGroupSerializer


@login_required
def os_list(request):

    oses = OS.objects.select_related()

    if 'search' in request.GET:
        terms = request.GET['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(name__icontains=term)
            query = query & q
        oses = oses.filter(query)
    else:
        terms = ''

    page_no = request.GET.get('page')
    paginator = Paginator(oses, 50)

    try:
        page = paginator.page(page_no)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    empty_oses = list(OS.objects.filter(host__isnull=True))

    return render(request,
                  'operatingsystems/os_list.html',
                  {'page': page, 'terms': terms, 'empty_oses': empty_oses}, )


@login_required
def os_detail(request, os_id):

    os = get_object_or_404(OS, id=os_id)

    if request.method == 'POST':
        create_form = CreateOSGroupForm(request.POST, prefix='create')
        if create_form.is_valid():
            osgroup = create_form.save()
            os.osgroup = osgroup
            os.save()
            text = 'Created OS Group {0!s} '.format(osgroup)
            text += 'and added OS {0!s} to it'.format(os)
            messages.info(request, text)
            return redirect(os.get_absolute_url())
        add_form = AddOSToOSGroupForm(request.POST, instance=os, prefix='add')
        if add_form.is_valid():
            add_form.save()
            text = 'OS {0!s} added to OS Group {1!s}'.format(os, os.osgroup)
            messages.info(request, text)
            return redirect(os.get_absolute_url())
    else:
        add_form = AddOSToOSGroupForm(instance=os, prefix='add')
        create_form = CreateOSGroupForm(prefix='create')

    return render(request,
                  'operatingsystems/os_detail.html',
                  {'os': os,
                   'add_form': add_form,
                   'create_form': create_form}, )


@login_required
def os_delete(request, os_id):

    if os_id == 'empty_oses':
        os = False
        oses = list(OS.objects.filter(host__isnull=True))
    else:
        os = get_object_or_404(OS, id=os_id)
        oses = False

    if request.method == 'POST':
        if 'delete' in request.POST:
            if os:
                os.delete()
                messages.info(request, 'OS {0!s} has been deleted'.format(os))
                return redirect(reverse('operatingsystems:os_list'))
            else:
                if not oses:
                    text = 'There are no OS\'s with no Hosts'
                    messages.info(request, text)
                    return redirect(reverse('operatingsystems:os_list'))
                for os in oses:
                    os.delete()
                text = '{0!s} OS\'s have been deleted'.format(len(oses))
                messages.info(request, text)
                return redirect(reverse('operatingsystems:os_list'))
        elif 'cancel' in request.POST:
            if os_id == 'empty_oses':
                return redirect(reverse('operatingsystems:os_list'))
            else:
                return redirect(os.get_absolute_url())

    return render(request,
                  'operatingsystems/os_delete.html',
                  {'os': os, 'oses': oses}, )


@login_required
def osgroup_list(request):

    osgroups = OSGroup.objects.select_related()

    if 'search' in request.GET:
        terms = request.GET['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(name__icontains=term)
            query = query & q
        osgroups = osgroups.filter(query)
    else:
        terms = ''

    page_no = request.GET.get('page')
    paginator = Paginator(osgroups, 50)

    try:
        page = paginator.page(page_no)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    return render(request,
                  'operatingsystems/osgroup_list.html',
                  {'page': page, 'terms': terms}, )


@login_required
def osgroup_detail(request, osgroup_id):

    osgroup = get_object_or_404(OSGroup, id=osgroup_id)

    if request.method == 'POST':
        repos_form = AddReposToOSGroupForm(request.POST, instance=osgroup)
        if repos_form.is_valid():
            repos_form.save()
            messages.info(request, 'Modified Repositories')
            return redirect(osgroup.get_absolute_url())

    repos_form = AddReposToOSGroupForm(instance=osgroup)

    return render(request,
                  'operatingsystems/osgroup_detail.html',
                  {'osgroup': osgroup, 'repos_form': repos_form}, )


@login_required
def osgroup_delete(request, osgroup_id):

    osgroup = get_object_or_404(OSGroup, id=osgroup_id)

    if request.method == 'POST':
        if 'delete' in request.POST:
            osgroup.delete()
            text = 'OS Group {0!s} has been deleted'.format(osgroup)
            messages.info(request, text)
            return redirect(reverse('operatingsystems:os_list'))
        elif 'cancel' in request.POST:
            return redirect(osgroup.get_absolute_url())

    return render(request,
                  'operatingsystems/osgroup_delete.html',
                  {'osgroup': osgroup}, )


class OSViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows operating systems to be viewed or edited.
    """
    queryset = OS.objects.all()
    serializer_class = OSSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)


class OSGroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows operating system groups to be viewed or edited.
    """
    queryset = OSGroup.objects.all()
    serializer_class = OSGroupSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
