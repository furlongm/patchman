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
from django.db import IntegrityError

from andsome.util.filterspecs import Filter, FilterBar

from patchman.hosts.models import HostRepo
from patchman.repos.models import Repository, Mirror
from patchman.operatingsystems.models import OSGroup
from patchman.arch.models import MachineArchitecture
from patchman.repos.forms import RepositoryForm, LinkRepoForm, CreateRepoForm


@login_required
def repo_list(request):

    repos = Repository.objects.select_related().order_by('name')

    if 'repotype' in request.REQUEST:
        repos = repos.filter(repotype=request.REQUEST['repotype'])

    if 'arch' in request.REQUEST:
        repos = repos.filter(arch=request.REQUEST['arch'])

    if 'osgroup' in request.REQUEST:
        repos = repos.filter(osgroup=request.REQUEST['osgroup'])

    if 'security' in request.REQUEST:
        security = request.REQUEST['security'] == 'True'
        repos = repos.filter(security=security)

    if 'enabled' in request.REQUEST:
        enabled = request.REQUEST['enabled'] == 'True'
        repos = repos.filter(enabled=enabled)

    if 'package_id' in request.REQUEST:
        repos = repos.filter(mirror__packages=int(request.REQUEST['package_id']))

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

    return render_to_response('repos/repo_list.html', {'page': page, 'filter_bar': filter_bar, 'terms': terms}, context_instance=RequestContext(request))


@login_required
def mirror_list(request):

    mirrors = Mirror.objects.select_related().order_by('file_checksum')

    if 'checksum' in request.REQUEST:
        checksum = request.REQUEST['checksum']
        mirrors = mirrors.filter(file_checksum=checksum)
    else:
        # only show mirrors with more than 0 packages
        # this is a hack but works, because a host with 0 packages has no packages with package_id > 0
        mirrors = mirrors.filter(packages__gt=0)
        # this is the correct way to do it, but the SQL takes way longer
        #mirrors = mirrors.annotate(num_packages=Count('packages')).filter(num_packages__gt=0)

    mirrors = mirrors.distinct()

    def pre_reqs(arch, repotype):
        for mirror in mirrors:
            if mirror.repo.arch != arch:
                messages.info(request, 'Not all mirror architectures are the same, cannot link to or create repos.')
                return render_to_response('repos/mirror_with_repo_list.html', {'page': page, 'checksum': checksum}, context_instance=RequestContext(request))
            if mirror.repo.repotype != repotype:
                messages.info(request, 'Not all mirror repotypes are the same, cannot link to or create repos.')
                return render_to_response('repos/mirror_with_repo_list.html', {'page': page, 'checksum': checksum}, context_instance=RequestContext(request))
        return True

    def move_mirrors(repo):
        for mirror in mirrors:
            oldrepo = mirror.repo
            for hostrepo in HostRepo.objects.filter(repo=oldrepo):
                try:
                    hostrepo.repo = repo
                    hostrepo.save()
                except IntegrityError:
                    hostrepo.delete()
            mirror.repo = repo
            mirror.save()
            if oldrepo.mirror_set.count() == 0:
                oldrepo.delete()

    try:
        page_no = int(request.GET.get('page', 1))
    except ValueError:
        page_no = 1

    p = Paginator(mirrors, 50)

    try:
        page = p.page(page_no)
    except (EmptyPage, InvalidPage):
        page = p.page(p.num_pages)

    if request.method == 'POST':
        arch = mirrors[0].repo.arch
        repotype = mirrors[0].repo.repotype

        enabled = mirrors[0].repo.enabled
        security = mirrors[0].repo.security

        create_form = CreateRepoForm(request.POST, prefix='create', arch=arch, repotype=repotype)
        if create_form.is_valid():
            repo = create_form.save(commit=False)
            repo.arch = create_form.arch
            repo.repotype = create_form.repotype
            repo.enabled = enabled
            repo.security = security
            repo.save()
            move_mirrors(repo)
            messages.info(request, 'Mirrors linked to new Repository %s' % repo)
            return HttpResponseRedirect(repo.get_absolute_url())

        link_form = LinkRepoForm(request.POST, prefix='link')
        if link_form.is_valid():
            repo = link_form.cleaned_data['name']
            move_mirrors(repo)
            messages.info(request, 'Mirrors linked to Repository %s' % repo)
            return HttpResponseRedirect(repo.get_absolute_url())

    else:
        if 'checksum' in request.REQUEST:
            arch = mirrors[0].repo.arch
            repotype = mirrors[0].repo.repotype
            prereqs = pre_reqs(arch, repotype)
            if prereqs != True:
                return prereqs
            else:
                link_form = LinkRepoForm(prefix='link')
                create_form = CreateRepoForm(prefix='create')
                return render_to_response('repos/mirror_with_repo_list.html', {'page': page, 'link_form': link_form, 'create_form': create_form, 'checksum': checksum}, context_instance=RequestContext(request))

    return render_to_response('repos/mirror_list.html', {'page': page}, context_instance=RequestContext(request))


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
                return HttpResponseRedirect(reverse('repo_detail', args=[repo_id]))
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
                return HttpResponseRedirect(reverse('repo_detail', args=[repo_id]))
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
                return HttpResponseRedirect(reverse('repo_detail', args=[repo_id]))
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
                return HttpResponseRedirect(reverse('repo_detail', args=[repo_id]))
        elif 'cancel' in request.REQUEST:
            return HttpResponseRedirect(reverse('repo_detail', args=[repo_id]))

    return render_to_response('repos/repo_endisablesec.html', {'repo': repo, 'enable': False}, context_instance=RequestContext(request))
