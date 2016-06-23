# Copyright 2012 VPAC, http://www.vpac.org
# Copyright 2013-2016 Marcus Furlong <furlongm@gmail.com>
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

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.http import Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q
from django.conf import settings
from django.contrib import messages

from patchman.util.filterspecs import Filter, FilterBar

from patchman.reports.models import Report


@csrf_exempt
def upload(request):

    response = HttpResponse()

    if request.method == 'POST':

        data = request.POST.copy()
        meta = request.META.copy()

        with transaction.atomic():
            report = Report.objects.create()
        report.parse(data, meta)
        if settings.USE_ASYNC_PROCESSING:
            from patchman.reports.tasks import process_report
            process_report.delay(report)

        if 'report' in data and data['report'] == '1':
            packages = []
            repos = []
            if 'packages' in data:
                for p in data['packages'].splitlines():
                    packages.append(p.replace('\'', '').split(' '))
            if 'repos' in data:
                repos = data['repos']
            return render(request,
                          'reports/report.txt',
                          {'data': data,
                           'packages': packages,
                           'repos': repos},
                          content_type='text/plain')
        else:
            # Should return HTTP 204
            response.status = 302
            return response
    else:
        raise Http404


@login_required
def report_list(request):

    reports = Report.objects.select_related()

    if 'host_id' in request.GET:
        reports = reports.filter(hostname=int(request.GET['host_id']))

    if 'processed' in request.GET:
        processed = request.GET['processed'] == 'True'
        reports = reports.filter(processed=processed)

    if 'search' in request.GET:
        terms = request.GET['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(host__icontains=term)
            query = query & q
        reports = reports.filter(query)
    else:
        terms = ''

    page_no = request.GET.get('page')
    paginator = Paginator(reports, 50)

    try:
        page = paginator.page(page_no)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    filter_list = []
    filter_list.append(Filter(request, 'processed',
                              {False: 'No', True: 'Yes'}))
    filter_bar = FilterBar(request, filter_list)

    return render(request,
                  'reports/report_list.html',
                  {'page': page,
                   'filter_bar': filter_bar,
                   'terms': terms}, )


@login_required
def report_detail(request, report):

    report = get_object_or_404(Report, id=report)

    return render(request,
                  'reports/report_detail.html',
                  {'report': report}, )


@login_required
def report_process(request, report):

    report = get_object_or_404(Report, id=report)

    return render(request,
                  'reports/report_process.html',
                  {'report': report}, )


@login_required
def report_delete(request, report):

    report = get_object_or_404(Report, id=report)

    if request.method == 'POST':
        if 'delete' in request.POST:
            report.delete()
            text = 'Report {0!s} has been deleted'.format(report)
            messages.info(request, text)
            return HttpResponseRedirect(reverse('report_list'))
        elif 'cancel' in request.POST:
            return HttpResponseRedirect(reverse('report_detail',
                                        args=[report.id]))
    return render(request,
                  'reports/report_delete.html',
                  {'report': report}, )
