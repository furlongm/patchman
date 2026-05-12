# Copyright 2025 Marcus Furlong <furlongm@gmail.com>
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

from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import get_object_or_404, render
from django_tables2 import RequestConfig
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets

from patchman.compliance.models import (
    ComplianceProfile, ComplianceResult, ComplianceRule, ComplianceScan,
)
from patchman.compliance.serializers import (
    ComplianceProfileSerializer, ComplianceRuleSerializer,
    ComplianceScanSerializer,
)
from patchman.compliance.tables import ComplianceResultTable, ComplianceScanTable
from patchman.hosts.models import Host


@login_required
def compliance_summary(request):
    """Fleet overview: latest scan per host, avg score, top failures."""
    latest_scan_ids = ComplianceScan.objects.values('host').annotate(
        latest_id=models.Max('id'),
    ).values_list('latest_id', flat=True)
    scans = ComplianceScan.objects.filter(
        id__in=latest_scan_ids,
    ).select_related('host', 'profile')

    total_hosts = scans.count()
    avg_score = scans.aggregate(avg=models.Avg('score'))['avg'] or 0

    top_failures = ComplianceResult.objects.filter(
        scan__in=scans, result='fail',
    ).values(
        'rule__rule_id', 'rule__severity',
    ).annotate(
        count=models.Count('id'),
    ).order_by('-count')[:10]

    table = ComplianceScanTable(scans)
    RequestConfig(request, paginate={'per_page': 50}).configure(table)

    return render(
        request,
        'compliance/compliance_summary.html',
        {
            'table': table,
            'total_hosts': total_hosts,
            'avg_score': avg_score,
            'top_failures': top_failures,
        },
    )


@login_required
def compliance_host(request, host_id):
    """Per-host detail: latest scan, rule results, history."""
    host = get_object_or_404(Host, pk=host_id)
    scans = ComplianceScan.objects.filter(
        host=host,
    ).select_related('profile')
    latest = scans.first()
    if latest:
        results = ComplianceResult.objects.filter(
            scan=latest,
        ).select_related('rule')
    else:
        results = ComplianceResult.objects.none()

    results_table = ComplianceResultTable(results)
    RequestConfig(request, paginate={'per_page': 50}).configure(results_table)

    return render(
        request,
        'compliance/compliance_host.html',
        {
            'host': host,
            'latest_scan': latest,
            'scans': scans,
            'results_table': results_table,
        },
    )


@login_required
def compliance_rule(request, rule_id):
    """Per-rule: which hosts pass/fail."""
    rule = get_object_or_404(ComplianceRule, pk=rule_id)
    latest_scan_ids = ComplianceScan.objects.values('host').annotate(
        latest_id=models.Max('id'),
    ).values_list('latest_id', flat=True)
    results = ComplianceResult.objects.filter(
        rule=rule, scan__in=latest_scan_ids,
    ).select_related('scan__host')

    return render(
        request,
        'compliance/compliance_rule.html',
        {
            'rule': rule,
            'results': results,
            'pass_count': results.filter(result='pass').count(),
            'fail_count': results.filter(result='fail').count(),
        },
    )


class ComplianceProfileViewSet(viewsets.ModelViewSet):
    """API endpoint that allows compliance profiles to be viewed or edited."""
    queryset = ComplianceProfile.objects.all()
    serializer_class = ComplianceProfileSerializer


class ComplianceRuleViewSet(viewsets.ModelViewSet):
    """API endpoint that allows compliance rules to be viewed or edited."""
    queryset = ComplianceRule.objects.all()
    serializer_class = ComplianceRuleSerializer


class ComplianceScanViewSet(viewsets.ModelViewSet):
    """API endpoint that allows compliance scans to be viewed or edited."""
    queryset = ComplianceScan.objects.all()
    serializer_class = ComplianceScanSerializer


class ComplianceStatsView(APIView):
    """API endpoint for compliance statistics."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        latest_scan_ids = ComplianceScan.objects.values('host').annotate(
            latest_id=models.Max('id'),
        ).values_list('latest_id', flat=True)
        scans = ComplianceScan.objects.filter(id__in=latest_scan_ids)

        total_hosts = scans.count()
        avg_score = scans.aggregate(avg=models.Avg('score'))['avg'] or 0

        # compliance by result
        results = ComplianceResult.objects.filter(scan__in=scans)
        compliance_by_result = {}
        for choice_value, _ in ComplianceResult.RESULT_CHOICES:
            compliance_by_result[choice_value] = results.filter(
                result=choice_value,
            ).count()

        # top failing rules
        top_failing = list(
            results.filter(result='fail').values(
                'rule__rule_id', 'rule__severity',
            ).annotate(
                count=models.Count('id'),
            ).order_by('-count')[:10]
        )

        # score distribution
        high = scans.filter(score__gt=90).count()
        medium = scans.filter(score__gte=70, score__lte=90).count()
        low = scans.filter(score__lt=70).count()

        return Response({
            'total_hosts_scanned': total_hosts,
            'average_score': round(avg_score, 1),
            'compliance_by_result': compliance_by_result,
            'top_failing_rules': top_failing,
            'score_distribution': {
                'high': high,
                'medium': medium,
                'low': low,
            },
        })
