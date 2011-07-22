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

from patchman.hosts.models import Host
from patchman.domains.models import Domain
from patchman.packages.models import Package, PackageName
from patchman.arch.models import MachineArchitecture
from patchman.repos.models import Repository
from patchman.operatingsystems.models import OS, OSGroup
from patchman.reports.models import Report

@login_required
def host_list(request):

    hosts = Host.objects.select_related()
    
    if request.REQUEST.has_key('domain'):
        hosts = hosts.filter(domain=int(request.GET['domain']))
    try:
        page_no = int(request.GET.get('page', 1))
    except ValueError:
        page_no = 1

    if request.REQUEST.has_key('package_id'):
        hosts = hosts.filter(packages=int(request.GET['package_id']))
    try:
        page_no = int(request.GET.get('page', 1))
    except ValueError:
        page_no = 1

    if request.REQUEST.has_key('package'):
         hosts = hosts.filter(packages__name__name=request.GET['package'])
    try:
        page_no = int(request.GET.get('page', 1))
    except ValueError:
        page_no = 1

    if request.REQUEST.has_key('repo'):
        hosts = hosts.filter(repos=int(request.GET['repo']))
    try:
        page_no = int(request.GET.get('page', 1))
    except ValueError:
        page_no = 1

    if request.REQUEST.has_key('arch'):
        hosts = hosts.filter(arch=int(request.GET['arch']))
    try:
        page_no = int(request.GET.get('page', 1))
    except ValueError:
        page_no = 1

    if request.REQUEST.has_key('os'):
        hosts = hosts.filter(os=int(request.GET['os']))
    try:
        page_no = int(request.GET.get('page', 1))
    except ValueError:
        page_no = 1

    if request.REQUEST.has_key('osgroup'):
        hosts = hosts.filter(os__osgroup=int(request.GET['osgroup']))
    try:
        page_no = int(request.GET.get('page', 1))
    except ValueError:
        page_no = 1

    if request.REQUEST.has_key('tag'):
         hosts = hosts.filter(tag=request.GET['tag'])
    try:
        page_no = int(request.GET.get('page', 1))
    except ValueError:
        page_no = 1

    if request.REQUEST.has_key('search'):
        new_data = request.POST.copy()
        terms = new_data['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(hostname__icontains = term)
            query = query & q

        hosts = hosts.filter(query)
    else:
        terms = ""

    p = Paginator(hosts, 50)

    try:
        page = p.page(page_no)
    except (EmptyPage, InvalidPage):
        page = p.page(p.num_pages)

    filter_list = []
    filter_list.append(Filter(request, 'tag', Host.objects.values_list('tag', flat=True).distinct()))
    filter_list.append(Filter(request, 'domain', Domain.objects.all()))
    filter_list.append(Filter(request, 'os', OS.objects.all()))
    filter_list.append(Filter(request, 'osgroup', OSGroup.objects.all()))
    filter_list.append(Filter(request, 'arch', MachineArchitecture.objects.all()))
    filter_bar = FilterBar(request, filter_list)

    return render_to_response('hosts/host_list.html', {'page': page, 'filter_bar': filter_bar}, context_instance=RequestContext(request))


@login_required
def host_detail(request, hostname):

    host = get_object_or_404(Host, hostname=hostname)

    try:
        reversedns = str(socket.gethostbyaddr(host.ipaddress)[0])
    except socket.gaierror:
        reversedns = 'None'

    reports = Report.objects.all().filter(host=hostname).order_by('-time')[:3]
    print reports
 
    return render_to_response('hosts/host_detail.html', {'host': host, 'reversedns': reversedns, 'reports': reports }, context_instance=RequestContext(request))

