# Copyright 2012 VPAC, http://www.vpac.org
# Copyright 2013-2021 Marcus Furlong <furlongm@gmail.com>
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

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db.utils import OperationalError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django_tables2 import RequestConfig
from tenacity import (
    retry, retry_if_exception_type, stop_after_attempt, wait_exponential,
)

from reports.models import Report
from reports.tables import ReportTable
from util import sanitize_filter_params
from util.filterspecs import Filter, FilterBar


def _get_filtered_reports(filter_params):
    """Helper to reconstruct filtered queryset from filter params."""
    from urllib.parse import parse_qs
    params = parse_qs(filter_params)

    reports = Report.objects.select_related()

    if 'host_id' in params:
        reports = reports.filter(hostname=params['host_id'][0])
    if 'processed' in params:
        processed = params['processed'][0] == 'true'
        reports = reports.filter(processed=processed)
    if 'search' in params:
        terms = params['search'][0].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(host__icontains=term)
            query = query & q
        reports = reports.filter(query)

    return reports


@retry(
    retry=retry_if_exception_type(OperationalError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=15),
)
@csrf_exempt
def upload(request):

    if request.method == 'POST':
        data = request.POST.copy()
        meta = request.META.copy()

        report = Report.objects.create()
        report.parse(data, meta)

        from reports.tasks import process_report
        process_report.delay(report.id)

        if 'report' in data and data['report'] == 'true':
            packages = []
            if 'packages' in data:
                for p in data['packages'].splitlines():
                    packages.append(p.replace("'", '').split(' '))
            repos = data.get('repos')
            modules = data.get('modules')
            sec_updates = data.get('sec_updates')
            bug_updates = data.get('bug_updates')
            return render(request,
                          'reports/report.txt',
                          {'data': data,
                           'packages': packages,
                           'modules': modules,
                           'sec_updates': sec_updates,
                           'bug_updates': bug_updates,
                           'repos': repos},
                          content_type='text/plain')
        else:
            return HttpResponse(status=204)
    else:
        raise Http404


@login_required
def report_list(request):

    reports = Report.objects.select_related()

    if 'host_id' in request.GET:
        reports = reports.filter(hostname=request.GET['host_id'])

    if 'processed' in request.GET:
        processed = request.GET['processed'] == 'true'
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

    filter_list = []
    filter_list.append(Filter(request, 'Processed', 'processed', {'true': 'Yes', 'false': 'No'}))
    filter_bar = FilterBar(request, filter_list)

    table = ReportTable(reports)
    RequestConfig(request, paginate={'per_page': 50}).configure(table)

    filter_params = sanitize_filter_params(request.GET.urlencode())
    bulk_actions = [
        {'value': 'process', 'label': 'Process'},
        {'value': 'delete', 'label': 'Delete'},
    ]

    return render(request,
                  'reports/report_list.html',
                  {'table': table,
                   'filter_bar': filter_bar,
                   'terms': terms,
                   'total_count': reports.count(),
                   'filter_params': filter_params,
                   'bulk_actions': bulk_actions})


@login_required
def report_detail(request, report_id):

    report = get_object_or_404(Report, id=report_id)

    return render(request,
                  'reports/report_detail.html',
                  {'report': report})


@login_required
def report_process(request, report_id):
    """ Process a report using a celery task
    """
    from reports.tasks import process_report
    report = get_object_or_404(Report, id=report_id)
    report.processed = False
    report.save()
    process_report.delay(report.id)
    text = f'Report {report} is being processed'
    messages.info(request, text)
    return redirect(report.get_absolute_url())


@login_required
def report_delete(request, report_id):

    report = get_object_or_404(Report, id=report_id)

    if request.method == 'POST':
        if 'delete' in request.POST:
            report.delete()
            text = f'Report {report} has been deleted'
            messages.info(request, text)
            return redirect(reverse('reports:report_list'))
        elif 'cancel' in request.POST:
            return redirect(report.get_absolute_url())

    return render(request,
                  'reports/report_delete.html',
                  {'report': report})


@login_required
def report_bulk_action(request):
    """Handle bulk actions on reports."""
    if request.method != 'POST':
        return redirect('reports:report_list')

    action = request.POST.get('action', '')
    select_all_filtered = request.POST.get('select_all_filtered') == '1'
    filter_params = request.POST.get('filter_params', '')

    if not action:
        messages.warning(request, 'Please select an action')
        if filter_params:
            return redirect(f"{reverse('reports:report_list')}?{filter_params}")
        return redirect('reports:report_list')

    if select_all_filtered:
        reports = _get_filtered_reports(filter_params)
    else:
        selected_ids = request.POST.getlist('selected_ids')
        if not selected_ids:
            messages.warning(request, 'No reports selected')
            if filter_params:
                return redirect(f"{reverse('reports:report_list')}?{filter_params}")
            return redirect('reports:report_list')
        reports = Report.objects.filter(id__in=selected_ids)

    count = reports.count()
    name = Report._meta.verbose_name if count == 1 else Report._meta.verbose_name_plural

    if action == 'process':
        from reports.tasks import process_report
        for report in reports:
            report.processed = False
            report.save()
            process_report.delay(report.id)
        messages.success(request, f'Queued {count} {name} for processing')
    elif action == 'delete':
        reports.delete()
        messages.success(request, f'Deleted {count} {name}')
    else:
        messages.warning(request, 'Invalid action')

    if filter_params:
        return redirect(f"{reverse('reports:report_list')}?{filter_params}")
    return redirect('reports:report_list')
