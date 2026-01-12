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

from security.models import CVE, CWE, Reference
from util.tables import BaseTable

# CVETable templates
CVE_ID_TEMPLATE = '<a href="{{ record.get_absolute_url }}">{{ record.cve_id }}</a>'
CVE_LINKS_TEMPLATE = (
    '{% load bootstrap3 %}'
    '<a href="https://nvd.nist.gov/vuln/detail/{{ record.cve_id }}">NIST {% bootstrap_icon "link" %}</a>'
    '&nbsp;&nbsp;'
    '<a href="https://www.cve.org/CVERecord?id={{ record.cve_id }}">MITRE {% bootstrap_icon "link" %}</a>'
    '&nbsp;&nbsp;'
    '<a href="https://osv.dev/vulnerability/{{ record.cve_id }}">osv.dev {% bootstrap_icon "link" %}</a>'
)
CVE_DESCRIPTION_TEMPLATE = (
    '<span class="expandable-text" data-full-text="{{ record.description }}">'
    '{{ record.description|truncatechars:60 }}</span>'
)
CVSS_SCORES_TEMPLATE = '{% for score in record.cvss_scores.all %} {{ score.score }} {% endfor %}'
CWES_TEMPLATE = '{% for cwe in record.cwes.all %} {{ cwe.cwe_id }} {% endfor %}'
CVE_ERRATA_TEMPLATE = (
    '<a href="{% url \'errata:erratum_list\' %}?cve_id={{ record.cve_id }}">'
    '{{ record.erratum_set.count }}</a>'
)

# CWETable templates
CWE_ID_TEMPLATE = '<a href="{{ record.get_absolute_url }}">{{ record.cwe_id }}</a>'
CWE_DESCRIPTION_TEMPLATE = (
    '<span class="expandable-text" data-full-text="{{ record.description }}">'
    '{{ record.description|truncatechars:120 }}</span>'
)
CWE_CVES_TEMPLATE = (
    '<a href="{% url \'security:cve_list\' %}?cwe_id={{ record.cwe_id }}">'
    '{{ record.cve_set.count }}</a>'
)

# ReferenceTable templates
REFERENCE_URL_TEMPLATE = '<a href="{{ record.url }}">{{ record.url }}</a>'
LINKED_ERRATA_TEMPLATE = (
    '<a href="{% url \'errata:erratum_list\' %}?reference_id={{ record.id }}">'
    '{{ record.erratum_set.count }}</a>'
)


class CVETable(BaseTable):
    cve_id = tables.TemplateColumn(
        CVE_ID_TEMPLATE,
        order_by='cve_id',
        verbose_name='CVE ID',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    links = tables.TemplateColumn(
        CVE_LINKS_TEMPLATE,
        orderable=False,
        verbose_name='Links',
        attrs={'th': {'class': 'col-sm-2'}, 'td': {'class': 'col-sm-2'}},
    )
    cve_description = tables.TemplateColumn(
        CVE_DESCRIPTION_TEMPLATE,
        orderable=False,
        verbose_name='Description',
        attrs={'th': {'class': 'col-sm-3'}, 'td': {'class': 'col-sm-3'}},
    )
    cvss_scores = tables.TemplateColumn(
        CVSS_SCORES_TEMPLATE,
        orderable=False,
        verbose_name='CVSS Scores',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    cwes = tables.TemplateColumn(
        CWES_TEMPLATE,
        orderable=False,
        verbose_name='CWEs',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    reserved_date = tables.DateColumn(
        order_by='reserved_date',
        verbose_name='Reserved',
        default='',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    rejected_date = tables.DateColumn(
        order_by='rejected_date',
        verbose_name='Rejected',
        default='',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    published_date = tables.DateColumn(
        order_by='published_date',
        verbose_name='Published',
        default='',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    updated_date = tables.DateColumn(
        order_by='updated_date',
        verbose_name='Updated',
        default='',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    cve_errata = tables.TemplateColumn(
        CVE_ERRATA_TEMPLATE,
        orderable=False,
        verbose_name='Errata',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )

    class Meta(BaseTable.Meta):
        model = CVE
        fields = (
            'cve_id', 'links', 'cve_description', 'cvss_scores', 'cwes',
            'reserved_date', 'rejected_date', 'published_date', 'updated_date', 'cve_errata',
        )


class CWETable(BaseTable):
    cwe_id = tables.TemplateColumn(
        CWE_ID_TEMPLATE,
        order_by='cwe_id',
        verbose_name='CWE ID',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    cwe_name = tables.Column(
        accessor='name',
        order_by='name',
        verbose_name='Name',
        default='',
        attrs={'th': {'class': 'col-sm-4'}, 'td': {'class': 'col-sm-4'}},
    )
    cwe_description = tables.TemplateColumn(
        CWE_DESCRIPTION_TEMPLATE,
        orderable=False,
        verbose_name='Description',
        attrs={'th': {'class': 'col-sm-6'}, 'td': {'class': 'col-sm-6'}},
    )
    cwe_cves = tables.TemplateColumn(
        CWE_CVES_TEMPLATE,
        orderable=False,
        verbose_name='CVEs',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )

    class Meta(BaseTable.Meta):
        model = CWE
        fields = ('cwe_id', 'cwe_name', 'cwe_description', 'cwe_cves')


class ReferenceTable(BaseTable):
    ref_type = tables.Column(
        order_by='ref_type',
        verbose_name='Type',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    reference_url = tables.TemplateColumn(
        REFERENCE_URL_TEMPLATE,
        orderable=False,
        verbose_name='URL',
        attrs={'th': {'class': 'col-sm-10'}, 'td': {'class': 'col-sm-10'}},
    )
    linked_errata = tables.TemplateColumn(
        LINKED_ERRATA_TEMPLATE,
        orderable=False,
        verbose_name='Linked Errata',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )

    class Meta(BaseTable.Meta):
        model = Reference
        fields = ('ref_type', 'reference_url', 'linked_errata')
