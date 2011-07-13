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

from patchman.packages.models import PackageName, Package
from patchman.repos.models import Repository

@login_required
def package_list(request):

    packages = PackageName.objects.select_related()
    
    try:
        page_no = int(request.GET.get('page', 1))
    except ValueError:
        page_no = 1

    if request.REQUEST.has_key('search'):
        new_data = request.POST.copy()
        terms = new_data['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(name__icontains = term)
            query = query & q

        packages = packages.filter(query)
    else:
        terms = ""

    p = Paginator(packages, 50)

    try:
        page = p.page(page_no)
    except (EmptyPage, InvalidPage):
        page = p.page(p.num_pages)

    filter_list = []
    filter_bar = FilterBar(request, filter_list)

    return render_to_response('packages/package_list.html', {'page': page, 'filter_bar': filter_bar}, context_instance=RequestContext(request))


@login_required
def package_detail(request, packagename):

    package = get_object_or_404(PackageName, name=packagename)
    allversions = Package.objects.select_related().filter(name=package.id)

    return render_to_response('packages/package_detail.html', {'package': package, 'allversions': allversions }, context_instance=RequestContext(request))

