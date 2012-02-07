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

from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.contrib import messages

from andsome.util.filterspecs import Filter, FilterBar

from patchman.repos.models import Repository
from patchman.operatingsystems.models import OSGroup
from patchman.arch.models import MachineArchitecture
from patchman.repos.forms import RepositoryForm


@login_required
def repo_list(request):

    repos = Repository.objects.select_related().order_by('name')

    if 'repotype' in request.REQUEST:
        repos = repos.filter(repotype=request.GET['repotype'])

    if 'arch' in request.REQUEST:
        repos = repos.filter(arch=request.GET['arch'])

    if 'osgroup' in request.REQUEST:
        repos = repos.filter(osgroup=request.GET['osgroup'])

    if 'security' in request.REQUEST:
        security = request.GET['security'] == 'True'
        repos = repos.filter(security=security)

    if 'enabled' in request.REQUEST:
        enabled = request.GET['enabled'] == 'True'
        repos = repos.filter(enabled=enabled)

    if 'package_id' in request.REQUEST:
        repos = repos.filter(mirror__packages=int(request.GET['package_id']))

    if 'search' in request.REQUEST:
        terms = request.REQUEST['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(name__icontains=term)
            query = query & q
        repos = repos.filter(query)
    else:
        terms = ''
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
    filter_list.append(Filter(request, 'enabled', {False: 'No', True: 'Yes'}))
    filter_list.append(Filter(request, 'security', {False: 'No', True: 'Yes'}))
    filter_list.append(Filter(request, 'osgroup', OSGroup.objects.all()))
    filter_bar = FilterBar(request, filter_list)

    return render_to_response('repos/repo_list.html', {'page': page, 'filter_bar': filter_bar}, context_instance=RequestContext(request))


@login_required
def repo_detail(request, repo_id):

    repo = get_object_or_404(Repository, id=repo_id)

    return render_to_response('repos/repo_detail.html', {'repo': repo}, context_instance=RequestContext(request))


@login_required
def repo_edit(request, repo_id):

    repo = get_object_or_404(Repository, id=repo_id)

    if request.method == 'POST':
        edit_form = RepositoryForm(request.POST, instance=repo)
        if edit_form.is_valid():
            repo = edit_form.save()
            repo.save()
            mirrors = edit_form.cleaned_data['mirrors']
            for mirror in mirrors:
                mirror.repo = repo
                mirror.save()
            messages.info(request, 'Saved changes to Repository %s' % repo)
            return HttpResponseRedirect(repo.get_absolute_url())
        else:
            repo = get_object_or_404(Repository, id=repo_id)
    else:
        edit_form = RepositoryForm(instance=repo)
        edit_form.initial['mirrors'] = repo.mirror_set.all()

    return render_to_response('repos/repo_edit.html', {'repo': repo, 'edit_form': edit_form}, context_instance=RequestContext(request))


@login_required
def repo_delete(request, repo_id):

    repo = get_object_or_404(Repository, id=repo_id)

    if request.method == 'POST':
        if 'delete' in request.REQUEST:
            repo.delete()
            messages.info(request, 'Repository %s has been deleted.' % repo)
            return HttpResponseRedirect(reverse('repo_list'))
        elif 'cancel' in request.REQUEST:
            return HttpResponseRedirect(reverse('repo_detail', args=[repo_id]))

    return render_to_response('repos/repo_delete.html', {'repo': repo}, context_instance=RequestContext(request))


@login_required
def repo_enable(request, repo_id):

    repo = get_object_or_404(Repository, id=repo_id)

    if request.method == 'POST':
        if 'enable' in request.REQUEST:
            repo.enabled = True
            repo.save()
            if request.is_ajax():
                return HttpResponse(status=204)
            else:
                messages.info(request, 'Repository %s has been enabled.' % repo)
                return HttpResponseRedirect(reverse('repo_list'))
        elif 'cancel' in request.REQUEST:
            return HttpResponseRedirect(reverse('repo_detail', args=[repo_id]))

    return render_to_response('repos/repo_endisable.html', {'repo': repo, 'enable': True}, context_instance=RequestContext(request))


@login_required
def repo_disable(request, repo_id):

    repo = get_object_or_404(Repository, id=repo_id)

    if request.method == 'POST':
        if 'disable' in request.REQUEST:
            repo.enabled = False
            repo.save()
            if request.is_ajax():
                return HttpResponse(status=204)
            else:
                messages.info(request, 'Repository %s has been disabled.' % repo)
                return HttpResponseRedirect(reverse('repo_list'))
        elif 'cancel' in request.REQUEST:
            return HttpResponseRedirect(reverse('repo_detail', args=[repo_id]))

    return render_to_response('repos/repo_endisable.html', {'repo': repo, 'enable': False}, context_instance=RequestContext(request))


@login_required
def repo_enablesec(request, repo_id):

    repo = get_object_or_404(Repository, id=repo_id)

    if request.method == 'POST':
        if 'enablesec' in request.REQUEST:
            repo.security = True
            repo.save()
            if request.is_ajax():
                return HttpResponse(status=204)
            else:
                messages.info(request, 'Repository %s has been marked as a security repo.' % repo)
                return HttpResponseRedirect(reverse('repo_list'))
        elif 'cancel' in request.REQUEST:
            return HttpResponseRedirect(reverse('repo_detail', args=[repo_id]))

    return render_to_response('repos/repo_endisablesec.html', {'repo': repo, 'enable': True}, context_instance=RequestContext(request))


@login_required
def repo_disablesec(request, repo_id):

    repo = get_object_or_404(Repository, id=repo_id)

    if request.method == 'POST':
        if 'disablesec' in request.REQUEST:
            repo.security = False
            repo.save()
            if request.is_ajax():
                return HttpResponse(status=204)
            else:
                messages.info(request, 'Repository %s has been marked as a non-security repo.' % repo)
                return HttpResponseRedirect(reverse('repo_list'))
        elif 'cancel' in request.REQUEST:
            return HttpResponseRedirect(reverse('repo_detail', args=[repo_id]))

    return render_to_response('repos/repo_endisablesec.html', {'repo': repo, 'enable': False}, context_instance=RequestContext(request))
