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

from andsome.util.filterspecs import Filter, FilterBar
from datetime import datetime, date, time
import socket

from patchman.operatingsystems.models import OS, OSGroup, LinkOSGroupForm, AddRepoToOSGroupForm
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
    form = LinkOSGroupForm()

    if request.method == 'POST':
        data = request.POST.copy()
        osgroup_id = data['osgroup']
        osgroup = OSGroup.objects.get(id=osgroup_id)
        os.osgroup = osgroup
        os.save()

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
    form = AddRepoToOSGroupForm()

    if request.method == 'POST':
        data = request.POST.copy()
        repo_id = data['repo']
        repo = Repository.objects.get(id=repo_id)
        osgroup.repos.add(repo)
        osgroup.save()

    return render_to_response('operatingsystems/osgroup_detail.html', {'osgroup': osgroup, 'form': form }, context_instance=RequestContext(request))
