# Copyright 2012 VPAC, http://www.vpac.org
# Copyright 2013-2025 Marcus Furlong <furlongm@gmail.com>
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

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db.utils import OperationalError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django_tables2 import RequestConfig
from rest_framework import status, viewsets
from rest_framework.response import Response
from tenacity import (
    retry, retry_if_exception_type, stop_after_attempt, wait_exponential,
)

from reports.models import Report
from reports.serializers import ReportUploadSerializer
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

    context = {'report': report}

    # Add tables for Protocol 2 reports
    if report.protocol == '2':
        from reports.tables import (
            ReportModuleTable, ReportPackageTable, ReportRepoTable,
            ReportUpdateTable,
        )
        if report.has_packages:
            context['packages_table'] = ReportPackageTable(report.packages_parsed)
        if report.has_repos:
            context['repos_table'] = ReportRepoTable(report.repos_parsed)
        if report.has_modules:
            context['modules_table'] = ReportModuleTable(report.modules_parsed)
        if report.has_sec_updates:
            context['sec_updates_table'] = ReportUpdateTable(report.sec_updates_parsed)
        if report.has_bug_updates:
            context['bug_updates_table'] = ReportUpdateTable(report.bug_updates_parsed)

    return render(request,
                  'reports/report_detail.html',
                  context)


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


class ReportViewSet(viewsets.ViewSet):
    """
    ViewSet for protocol 2 JSON report uploads and report listing.

    GET /api/report/ - List all reports
    GET /api/report/{id}/ - Retrieve a single report
    POST /api/report/ - Upload a new report in JSON format

    Authentication is optional by default. Set REQUIRE_API_KEY=True in settings
    to require API key authentication for report uploads.
    """

    def get_permissions(self):
        from django.conf import settings
        from rest_framework.permissions import (
            AllowAny, IsAuthenticatedOrReadOnly,
        )
        from rest_framework_api_key.permissions import HasAPIKey

        # POST requires API key if configured, otherwise allow any
        if self.action == 'create':
            if getattr(settings, 'REQUIRE_API_KEY', False):
                return [HasAPIKey()]
            return [AllowAny()]
        # GET is read-only (authenticated or read-only)
        return [IsAuthenticatedOrReadOnly()]

    def list(self, request):
        """List all reports."""
        from reports.serializers import ReportSerializer
        queryset = Report.objects.all().order_by('-created')
        serializer = ReportSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Retrieve a single report."""
        from django.shortcuts import get_object_or_404

        from reports.serializers import ReportSerializer
        report = get_object_or_404(Report, pk=pk)
        serializer = ReportSerializer(report, context={'request': request})
        return Response(serializer.data)

    def create(self, request):
        """Handle protocol 2 JSON report upload."""
        serializer = ReportUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'status': 'error', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data

        # Extract client IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_forwarded_for:
            report_ip = x_forwarded_for.split(',')[0]
        elif x_real_ip:
            report_ip = x_real_ip
        else:
            report_ip = request.META.get('REMOTE_ADDR')

        # Extract domain from hostname
        hostname = data['hostname'].lower()
        domain = None
        fqdn = hostname.split('.', 1)
        if len(fqdn) == 2:
            domain = fqdn[1]

        # Convert tags list to comma-separated string
        tags = ','.join(data.get('tags', []))

        # Convert reboot_required to string for compatibility
        reboot = 'True' if data.get('reboot_required') else 'False'

        # Store JSON data as strings in the report model
        report = Report.objects.create(
            host=hostname,
            domain=domain,
            tags=tags,
            kernel=data['kernel'],
            arch=data['arch'],
            os=data['os'],
            report_ip=report_ip,
            protocol='2',
            useragent=request.META.get('HTTP_USER_AGENT', ''),
            packages=json.dumps(data.get('packages', [])),
            repos=json.dumps(data.get('repos', [])),
            modules=json.dumps(data.get('modules', [])),
            sec_updates=json.dumps(data.get('sec_updates', [])),
            bug_updates=json.dumps(data.get('bug_updates', [])),
            reboot=reboot,
        )

        # Queue for async processing
        from reports.tasks import process_report
        process_report.delay(report.id)

        return Response(
            {
                'status': 'accepted',
                'report_id': report.id,
                'message': 'Report queued for processing'
            },
            status=status.HTTP_202_ACCEPTED
        )
