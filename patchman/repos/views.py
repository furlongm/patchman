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

from patchman.packages.models import PackageName, Package
from patchman.repos.models import Repository
from patchman.operatingsystems.models import OSGroup
from patchman.arch.models import MachineArchitecture

@login_required
def repo_list(request):

    repos = Repository.objects.select_related().order_by('name')

    if request.REQUEST.has_key('repotype'):
        repos = repos.filter(repotype=request.GET['repotype'])

    if request.REQUEST.has_key('arch'):
        repos = repos.filter(arch=request.GET['arch'])

    if request.REQUEST.has_key('osgroup'):
        repos = repos.filter(osgroup=request.GET['osgroup'])

    if request.REQUEST.has_key('security'):
        security = request.GET['security'] == 'True'
        repos = repos.filter(security=security)

    if request.REQUEST.has_key('enabled'):
        enabled = request.GET['enabled'] == 'True'
        repos = repos.filter(enabled=enabled)
    
    if request.REQUEST.has_key('package_id'):
        repos = repos.filter(mirror__packages=int(request.GET['package_id']))

    if request.REQUEST.has_key('search'):
        terms = request.REQUEST['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(name__icontains = term)
            query = query & q
        repos = repos.filter(query)
    else:
        terms = ""
    repos = repos.distinct()
    try:
        page_no = int(request.GET.get('page', 1))
    except ValueError:
        page_no = 1

    p = Paginator(repos, 50)

    try:
        page = p.page(page_no)
    except (EmptyPage, InvalidPage):
        page = p.page(p.num_pages)

    filter_list = []
    filter_list.append(Filter(request, 'repotype', Repository.objects.values_list('repotype', flat=True).distinct()))
    filter_list.append(Filter(request, 'arch', MachineArchitecture.objects.all()))
    filter_list.append(Filter(request, 'enabled', Repository.objects.values_list('enabled', flat=True).distinct()))
    filter_list.append(Filter(request, 'security', Repository.objects.values_list('security', flat=True).distinct()))
    filter_list.append(Filter(request, 'osgroup', OSGroup.objects.all()))
    filter_bar = FilterBar(request, filter_list)

    return render_to_response('repos/repo_list.html', {'page': page, 'filter_bar': filter_bar}, context_instance=RequestContext(request))


@login_required
def repo_detail(request, repo):

    repo = get_object_or_404(Repository, id=repo)

    return render_to_response('repos/repo_detail.html', {'repo': repo }, context_instance=RequestContext(request))

@login_required
def repo_delete(request, repo):

    repo = get_object_or_404(Repository, id=repo)

    if request.method == 'POST':
        if request.REQUEST.has_key('delete'):
            repo.delete()
            messages.info(request, "Repository %s has been deleted." % repo)
            return HttpResponseRedirect(reverse('repo_list'))
        elif request.REQUEST.has_key('cancel'):
            return HttpResponseRedirect(reverse('repo_detail', args=[repo]))

    return render_to_response('repos/repo_delete.html', {'repo': repo }, context_instance=RequestContext(request))
