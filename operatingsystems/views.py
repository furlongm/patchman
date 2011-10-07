# Copyright 2011 VPAC <furlongm@vpac.org>
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

from django.utils.datastructures import MultiValueDictKeyError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import permission_required, login_required
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count
from django.contrib import messages

from andsome.util.filterspecs import Filter, FilterBar
from datetime import datetime, date, time
import socket

from patchman.operatingsystems.models import OS, OSGroup
from patchman.operatingsystems.forms import LinkOSGroupForm, AddReposToOSGroupForm
from patchman.repos.models import Repository

@login_required
def os_list(request):

    oses = OS.objects.select_related()
    
    try:
        page_no = int(request.GET.get('page', 1))
    except ValueError:
        page_no = 1

    if request.method == 'POST':
        new_data = request.POST.copy()
        terms = new_data['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(name__icontains = term)
            query = query & q
        oses = oses.filter(query)
    else:
        terms = ""

    p = Paginator(oses, 50)

    try:
        page = p.page(page_no)
    except (EmptyPage, InvalidPage):
        page = p.page(p.num_pages)

    filter_list = []
    filter_bar = FilterBar(request, filter_list)

    return render_to_response('operatingsystems/os_list.html', {'page': page, 'filter_bar': filter_bar}, context_instance=RequestContext(request))


@login_required
def os_detail(request, os_id):

    os = get_object_or_404(OS, id=os_id)

    if request.method == 'POST':
        form = LinkOSGroupForm(request.POST, instance=os)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(os.get_absolute_url())

    form = LinkOSGroupForm(instance=os)

    return render_to_response('operatingsystems/os_detail.html', {'os': os, 'form': form }, context_instance=RequestContext(request))

@login_required
def osgroup_list(request):

    osgroups = OSGroup.objects.select_related()

    try:
        page_no = int(request.GET.get('page', 1))
    except ValueError:
        page_no = 1

    if request.method == 'POST':
        new_data = request.POST.copy()
        terms = new_data['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(name__icontains = term)
            query = query & q
        osgroups = osgroups.filter(query)
    else:
        terms = ""

    p = Paginator(osgroups, 50)

    try:
        page = p.page(page_no)
    except (EmptyPage, InvalidPage):
        page = p.page(p.num_pages)

    filter_list = []
    filter_bar = FilterBar(request, filter_list)

    return render_to_response('operatingsystems/osgroup_list.html', {'page': page, 'filter_bar': filter_bar}, context_instance=RequestContext(request))

@login_required
def osgroup_detail(request, osgroup_id):

    osgroup = get_object_or_404(OSGroup, id=osgroup_id)

    if request.method == 'POST':
        form = AddReposToOSGroupForm(request.POST, instance=osgroup)
        if form.is_valid():
            form.save()
            messages.info(request, "Modified Repositories")
            return HttpResponseRedirect(osgroup.get_absolute_url())

    form = AddReposToOSGroupForm(instance=osgroup)

    return render_to_response('operatingsystems/osgroup_detail.html', {'osgroup': osgroup, 'form': form }, context_instance=RequestContext(request))
