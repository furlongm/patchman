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

import django_tables2 as tables

from patchman.compliance.models import ComplianceResult, ComplianceScan
from patchman.util.tables import BaseTable

SCAN_HOST_TEMPLATE = (
    '<a href="{% url \'compliance:compliance_host\' record.host.id %}">'
    '{{ record.host.hostname }}</a>'
)
SCAN_PROFILE_TEMPLATE = '{{ record.profile.profile_id }}'
SCAN_SCORE_TEMPLATE = '{{ record.score }}/{{ record.score_maximum }}'

RESULT_RULE_TEMPLATE = (
    '<a href="{% url \'compliance:compliance_rule\' record.rule.id %}">'
    '{{ record.rule.rule_id }}</a>'
)
RESULT_BADGE_TEMPLATE = (
    '{% if record.result == "pass" %}'
    '<span class="label label-success">{{ record.result }}</span>'
    '{% elif record.result == "fail" %}'
    '<span class="label label-danger">{{ record.result }}</span>'
    '{% elif record.result == "error" %}'
    '<span class="label label-warning">{{ record.result }}</span>'
    '{% else %}'
    '<span class="label label-default">{{ record.result }}</span>'
    '{% endif %}'
)


class ComplianceScanTable(BaseTable):
    host = tables.TemplateColumn(
        SCAN_HOST_TEMPLATE,
        orderable=True,
        verbose_name='Host',
        attrs={'th': {'class': 'col-sm-2'}, 'td': {'class': 'col-sm-2'}},
    )
    profile = tables.TemplateColumn(
        SCAN_PROFILE_TEMPLATE,
        orderable=True,
        verbose_name='Profile',
        attrs={'th': {'class': 'col-sm-3'}, 'td': {'class': 'col-sm-3'}},
    )
    score = tables.TemplateColumn(
        SCAN_SCORE_TEMPLATE,
        orderable=True,
        verbose_name='Score',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    pass_count = tables.Column(
        verbose_name='Pass',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    fail_count = tables.Column(
        verbose_name='Fail',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    error_count = tables.Column(
        verbose_name='Error',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    scanned_at = tables.DateTimeColumn(
        verbose_name='Scanned',
        attrs={'th': {'class': 'col-sm-2'}, 'td': {'class': 'col-sm-2'}},
    )

    class Meta(BaseTable.Meta):
        model = ComplianceScan
        fields = (
            'host', 'profile', 'score', 'pass_count',
            'fail_count', 'error_count', 'scanned_at',
        )


class ComplianceResultTable(BaseTable):
    rule = tables.TemplateColumn(
        RESULT_RULE_TEMPLATE,
        orderable=True,
        verbose_name='Rule',
        attrs={'th': {'class': 'col-sm-5'}, 'td': {'class': 'col-sm-5'}},
    )
    severity = tables.Column(
        accessor='rule.severity',
        verbose_name='Severity',
        attrs={'th': {'class': 'col-sm-2'}, 'td': {'class': 'col-sm-2'}},
    )
    result = tables.TemplateColumn(
        RESULT_BADGE_TEMPLATE,
        orderable=True,
        verbose_name='Result',
        attrs={'th': {'class': 'col-sm-2'}, 'td': {'class': 'col-sm-2'}},
    )

    class Meta(BaseTable.Meta):
        model = ComplianceResult
        fields = ('rule', 'severity', 'result')
