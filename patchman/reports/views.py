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
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, render_to_response
from django.contrib.auth.decorators import permission_required, login_required
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.http import Http404
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.db.models import Q, Count

from andsome.util.filterspecs import Filter, FilterBar
from datetime import datetime, date, time

from patchman.reports.models import Report
from patchman.reports.tasks import process_reports, find_host_updates

@csrf_exempt
def upload(request):

    response = HttpResponse()
    
    if request.method == 'POST':
        
        data = request.POST.copy()
        meta = request.META.copy()

        report = Report.objects.create()
        report.parse(data, meta)
        process_reports.delay(report.host)
        find_host_updates.delay(report.host)

        if 'report' in data and data['report'] == '1':
            packages = []
            if 'packages' in data:
                for p in data['packages'].splitlines():
                    packages.append(p.replace('\'','').split(' '))
            return render_to_response('reports/report.txt', {'data':data, 'packages':packages}, context_instance=RequestContext(request), mimetype='text/plain')
        else:
            # Should return HTTP 204
            response.status=302
            return response
    else:
        raise Http404

@login_required
def report_list(request):

    reports = Report.objects.select_related()

    try:
        page_no = int(request.GET.get('page', 1))
    except ValueError:
        page_no = 1

    if request.REQUEST.has_key('host_id'):
        reports = reports.filter(hostname=int(request.GET['host_id']))
    try:
        page_no = int(request.GET.get('page', 1))
    except ValueError:
        page_no = 1

    if request.method == 'POST':
        new_data = request.POST.copy()
        terms = new_data['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(host__icontains = term)
            query = query & q
        reports = reports.filter(query)
    else:
        terms = ""

    p = Paginator(reports, 50)

    try:
        page = p.page(page_no)
    except (EmptyPage, InvalidPage):
        page = p.page(p.num_pages)

    filter_list = []
    filter_bar = FilterBar(request, filter_list)

    return render_to_response('reports/report_list.html', {'page': page, 'filter_bar': filter_bar}, context_instance=RequestContext(request))


@login_required
def report_detail(request, report):

    report = get_object_or_404(Report, id=report)

    return render_to_response('reports/report_detail.html', {'report': report }, context_instance=RequestContext(request))

