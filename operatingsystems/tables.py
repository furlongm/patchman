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

from operatingsystems.models import OSRelease, OSVariant
from util.tables import BaseTable

CHECKBOX_TEMPLATE = '<input type="checkbox" name="selected_ids" value="{{ record.id }}" class="bulk-checkbox">'
SELECT_ALL_CHECKBOX = '<input type="checkbox" id="select-all-page" title="Select all on this page">'

# OSReleaseTable templates
OSRELEASE_NAME_TEMPLATE = '<a href="{{ record.get_absolute_url }}">{{ record.name }}</a>'
OSRELEASE_REPOS_TEMPLATE = (
    '<a href="{% url \'repos:repo_list\' %}?osrelease_id={{ record.id }}">'
    '{{ record.repos.count }}</a>'
)
OSVARIANTS_TEMPLATE = (
    '<a href="{% url \'operatingsystems:osvariant_list\' %}?osrelease_id={{ record.id }}">'
    '{{ record.osvariant_set.count }}</a>'
)
OSRELEASE_HOSTS_TEMPLATE = (
    '{% load common %}'
    '<a href="{% url \'hosts:host_list\' %}?osrelease_id={{ record.id }}">{% host_count record %}</a>'
)
OSRELEASE_ERRATA_TEMPLATE = (
    '<a href="{% url \'errata:erratum_list\' %}?osrelease_id={{ record.id }}">'
    '{{ record.erratum_set.count }}</a>'
)

# OSVariantTable templates
OSVARIANT_NAME_TEMPLATE = '<a href="{{ record.get_absolute_url }}">{{ record }}</a>'
OSVARIANT_CODENAME_TEMPLATE = (
    '{% if record.codename %}{{ record.codename }}'
    '{% else %}{% if record.osrelease %}{{ record.osrelease.codename }}{% endif %}{% endif %}'
)
OSVARIANT_HOSTS_TEMPLATE = (
    '<a href="{% url \'hosts:host_list\' %}?osvariant_id={{ record.id }}">'
    '{{ record.host_set.count }}</a>'
)
OSVARIANT_OSRELEASE_TEMPLATE = (
    '{% if record.osrelease %}'
    '<a href="{{ record.osrelease.get_absolute_url }}">{{ record.osrelease }}</a>'
    '{% endif %}'
)
REPOS_OSRELEASE_TEMPLATE = (
    '{% if record.osrelease.repos.count != None %}{{ record.osrelease.repos.count }}{% else %}0{% endif %}'
)


class OSReleaseTable(BaseTable):
    selection = tables.TemplateColumn(
        CHECKBOX_TEMPLATE,
        orderable=False,
        verbose_name=SELECT_ALL_CHECKBOX,
        attrs={'th': {'class': 'min-width-col centered'}, 'td': {'class': 'min-width-col centered'}},
    )
    osrelease_name = tables.TemplateColumn(
        OSRELEASE_NAME_TEMPLATE,
        order_by='name',
        verbose_name='OS Release',
        attrs={'th': {'class': 'col-sm-3'}, 'td': {'class': 'col-sm-3'}},
    )
    cpe_name = tables.Column(
        verbose_name='CPE Name',
        default='',
        attrs={'th': {'class': 'col-sm-2'}, 'td': {'class': 'col-sm-2'}},
    )
    osrelease_codename = tables.Column(
        accessor='codename',
        verbose_name='Codename',
        default='',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    osrelease_repos = tables.TemplateColumn(
        OSRELEASE_REPOS_TEMPLATE,
        verbose_name='Repos',
        orderable=False,
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    osvariants = tables.TemplateColumn(
        OSVARIANTS_TEMPLATE,
        verbose_name='OS Variants',
        orderable=False,
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    osrelease_hosts = tables.TemplateColumn(
        OSRELEASE_HOSTS_TEMPLATE,
        verbose_name='Hosts',
        orderable=False,
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    osrelease_errata = tables.TemplateColumn(
        OSRELEASE_ERRATA_TEMPLATE,
        verbose_name='Errata',
        orderable=False,
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )

    class Meta(BaseTable.Meta):
        model = OSRelease
        fields = (
            'selection', 'osrelease_name', 'cpe_name', 'osrelease_codename', 'osrelease_repos',
            'osvariants', 'osrelease_hosts', 'osrelease_errata',
        )


class OSVariantTable(BaseTable):
    selection = tables.TemplateColumn(
        CHECKBOX_TEMPLATE,
        orderable=False,
        verbose_name=SELECT_ALL_CHECKBOX,
        attrs={'th': {'class': 'min-width-col centered'}, 'td': {'class': 'min-width-col centered'}},
    )
    osvariant_name = tables.TemplateColumn(
        OSVARIANT_NAME_TEMPLATE,
        order_by='name',
        verbose_name='Name',
        attrs={'th': {'class': 'col-sm-3'}, 'td': {'class': 'col-sm-3'}},
    )
    osvariant_arch = tables.Column(
        accessor='arch__name',
        default='',
        verbose_name='Architecture',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    osvariant_codename = tables.TemplateColumn(
        OSVARIANT_CODENAME_TEMPLATE,
        order_by='codename',
        verbose_name='Codename',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    osvariant_hosts = tables.TemplateColumn(
        OSVARIANT_HOSTS_TEMPLATE,
        verbose_name='Hosts',
        order_by='hosts_count',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    osrelease = tables.TemplateColumn(
        OSVARIANT_OSRELEASE_TEMPLATE,
        order_by='osrelease__name',
        verbose_name='OS Release',
        attrs={'th': {'class': 'col-sm-4'}, 'td': {'class': 'col-sm-4'}},
    )
    repos_osrelease = tables.TemplateColumn(
        REPOS_OSRELEASE_TEMPLATE,
        verbose_name='Repos (OS Release)',
        order_by='repos_count',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )

    class Meta(BaseTable.Meta):
        model = OSVariant
        fields = (
            'selection', 'osvariant_name', 'osvariant_arch', 'osvariant_codename',
            'osvariant_hosts', 'osrelease', 'repos_osrelease',
        )
