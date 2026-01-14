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

from errata.models import Erratum
from util.tables import BaseTable

ERRATUM_NAME_TEMPLATE = '<a href="{{ record.get_absolute_url }}">{{ record.name }}</a>'
PACKAGES_AFFECTED_TEMPLATE = (
    '{% with count=record.affected_packages.count %}'
    '{% if count != 0 %}'
    '<a href="{% url \'packages:package_list\' %}?erratum_id={{ record.id }}&type=affected">{{ count }}</a>'
    '{% else %}{% endif %}{% endwith %}'
)
PACKAGES_FIXED_TEMPLATE = (
    '{% with count=record.fixed_packages.count %}'
    '{% if count != 0 %}'
    '<a href="{% url \'packages:package_list\' %}?erratum_id={{ record.id }}&type=fixed">{{ count }}</a>'
    '{% else %}{% endif %}{% endwith %}'
)
OSRELEASES_TEMPLATE = (
    '{% with count=record.osreleases.count %}'
    '{% if count != 0 %}'
    '<a href="{% url \'operatingsystems:osrelease_list\' %}?erratum_id={{ record.id }}">{{ count }}</a>'
    '{% else %}{% endif %}{% endwith %}'
)
ERRATUM_CVES_TEMPLATE = (
    '{% with count=record.cves.count %}'
    '{% if count != 0 %}'
    '<a href="{% url \'security:cve_list\' %}?erratum_id={{ record.id }}">{{ count }}</a>'
    '{% else %}{% endif %}{% endwith %}'
)
REFERENCES_TEMPLATE = (
    '{% with count=record.references.count %}'
    '{% if count != 0 %}'
    '<a href="{% url \'security:reference_list\' %}?erratum_id={{ record.id }}">{{ count }}</a>'
    '{% else %}{% endif %}{% endwith %}'
)


class ErratumTable(BaseTable):
    erratum_name = tables.TemplateColumn(
        ERRATUM_NAME_TEMPLATE,
        order_by='name',
        verbose_name='ID',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    e_type = tables.Column(
        order_by='e_type',
        verbose_name='Type',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    issue_date = tables.DateColumn(
        order_by='issue_date',
        verbose_name='Published Date',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    synopsis = tables.Column(
        orderable=False,
        verbose_name='Synopsis',
        attrs={'th': {'class': 'col-sm-4'}, 'td': {'class': 'col-sm-4'}},
    )
    packages_affected = tables.TemplateColumn(
        PACKAGES_AFFECTED_TEMPLATE,
        orderable=False,
        verbose_name='Packages Affected',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    packages_fixed = tables.TemplateColumn(
        PACKAGES_FIXED_TEMPLATE,
        orderable=False,
        verbose_name='Packages Fixed',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    osreleases = tables.TemplateColumn(
        OSRELEASES_TEMPLATE,
        orderable=False,
        verbose_name='OS Releases Affected',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    erratum_cves = tables.TemplateColumn(
        ERRATUM_CVES_TEMPLATE,
        orderable=False,
        verbose_name='CVEs',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    references = tables.TemplateColumn(
        REFERENCES_TEMPLATE,
        orderable=False,
        verbose_name='References',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )

    class Meta(BaseTable.Meta):
        model = Erratum
        fields = (
            'erratum_name', 'e_type', 'issue_date', 'synopsis', 'packages_affected',
            'packages_fixed', 'osreleases', 'erratum_cves', 'references',
        )
