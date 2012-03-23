# Copyright 2012 VPAC, http://www.vpac.org
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

from django.shortcuts import get_object_or_404, render_to_response, get_list_or_404
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.db.models import Q
from django.contrib import messages
from django.core.urlresolvers import reverse

from patchman.operatingsystems.models import OS, OSGroup
from patchman.operatingsystems.forms import LinkOSGroupForm, AddReposToOSGroupForm, CreateOSGroupForm


@login_required
def os_list(request):

    oses = OS.objects.select_related()

    try:
        page_no = int(request.GET.get('page', 1))
    except ValueError:
        page_no = 1

    if 'search' in request.REQUEST:
        terms = request.REQUEST['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(name__icontains=term)
            query = query & q
        oses = oses.filter(query)
    else:
        terms = ''
    p = Paginator(oses, 50)

    try:
        page = p.page(page_no)
    except (EmptyPage, InvalidPage):
        page = p.page(p.num_pages)

    return render_to_response('operatingsystems/os_list.html', {'page': page, 'terms': terms}, context_instance=RequestContext(request))


@login_required
def os_detail(request, os_id):

    os = get_object_or_404(OS, id=os_id)

    if request.method == 'POST':
        create_form = CreateOSGroupForm(request.POST, prefix='create')
        if create_form.is_valid():
            osgroup = create_form.save()
            os.osgroup = osgroup
            os.save()
            messages.info(request, 'Created and linked to new OS Group')
            return HttpResponseRedirect(os.get_absolute_url())
        link_form = LinkOSGroupForm(request.POST, instance=os, prefix='link')
        if link_form.is_valid():
            link_form.save()
            messages.info(request, 'Link to OS Group successful')
            return HttpResponseRedirect(os.get_absolute_url())
    else:
        link_form = LinkOSGroupForm(instance=os, prefix='link')
        create_form = CreateOSGroupForm(prefix='create')

    return render_to_response('operatingsystems/os_detail.html', {'os': os, 'link_form': link_form, 'create_form': create_form}, context_instance=RequestContext(request))


@login_required
def os_delete(request, os_id):

    if os_id == 'empty_oses':
        os = False
        oses = get_list_or_404(OS.objects.filter(host__isnull=True))
    else:
        os = get_object_or_404(OS, id=os_id)
        oses = False

    if request.method == 'POST':
        if 'delete' in request.REQUEST:
            if os:
                os.delete()
                messages.info(request, 'OS %s has been deleted' % os)
                return HttpResponseRedirect(reverse('os_list'))
            if oses:
                for os in oses:
                    os.delete()
                messages.info(request, '%s OS\'s have been deleted' % len(oses))
                return HttpResponseRedirect(reverse('os_list'))
        elif 'cancel' in request.REQUEST:
            if os_id == 'empty_oses':
                return HttpResponseRedirect(reverse('os_list'))
            else:
                return HttpResponseRedirect(reverse('os_detail', args=[os_id]))

    return render_to_response('operatingsystems/os_delete.html', {'os': os, 'oses': oses}, context_instance=RequestContext(request))


@login_required
def osgroup_list(request):

    osgroups = OSGroup.objects.select_related()

    try:
        page_no = int(request.GET.get('page', 1))
    except ValueError:
        page_no = 1

    if 'search' in request.REQUEST:
        terms = request.REQUEST['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(name__icontains=term)
            query = query & q
        osgroups = osgroups.filter(query)
    else:
        terms = ''

    p = Paginator(osgroups, 50)

    try:
        page = p.page(page_no)
    except (EmptyPage, InvalidPage):
        page = p.page(p.num_pages)

    return render_to_response('operatingsystems/osgroup_list.html', {'page': page}, context_instance=RequestContext(request))


@login_required
def osgroup_detail(request, osgroup_id):

    osgroup = get_object_or_404(OSGroup, id=osgroup_id)

    if request.method == 'POST':
        form = AddReposToOSGroupForm(request.POST, instance=osgroup)
        if form.is_valid():
            form.save()
            messages.info(request, 'Modified Repositories')
            return HttpResponseRedirect(osgroup.get_absolute_url())

    form = AddReposToOSGroupForm(instance=osgroup)

    return render_to_response('operatingsystems/osgroup_detail.html', {'osgroup': osgroup, 'form': form}, context_instance=RequestContext(request))


@login_required
def osgroup_delete(request, osgroup_id):

    osgroup = get_object_or_404(OSGroup, id=osgroup_id)

    if request.method == 'POST':
        if 'delete' in request.REQUEST:
            osgroup.delete()
            messages.info(request, 'OS Group %s has been deleted' % osgroup)
            return HttpResponseRedirect(reverse('os_list'))
        elif 'cancel' in request.REQUEST:
            return HttpResponseRedirect(reverse('osgroup_detail', args=[osgroup_id]))

    return render_to_response('operatingsystems/osgroup_delete.html', {'osgroup': osgroup}, context_instance=RequestContext(request))
